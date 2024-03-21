import os
import dotenv

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts.chat import MessagesPlaceholder
from langchain.globals import set_debug
from langchain_openai import ChatOpenAI
from langchain.tools import StructuredTool

# DO NOT REMOVE! May require next time
# TODO: Merge router into navigation
from tools.route_finder import get_routes_tool
from tools.route_info_retrieval import (
    retrieve_incidents_tool,
    retrieve_parking_lots_tool,
)
from tools.route_evaluation import (
    evaluate_route_tool,
    rank_routes_tool,
)

from custom_logger import logger

config = dotenv.dotenv_values(".env")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

set_debug(True)


class LangchainInterface:
    def __init__(self, debug_mode=False):
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """ 
                    You're a Singapore Land Transport Authority customer support agent, tasked with answering
                    user queries on Telegram.
                    In this case, the user is asking about the best route from point A to point B.

                    Always make sure that you understand the user's origin and destination. If the user only
                    provided their destination, you may ask for their origin point. You do not need to ask if
                    they will be taking private or public transport, since you will be giving options for both.

                    To discover and evaluate routes from the user's origin to their destination, you can use
                    the following tools:

                    1. Route-finding function for turn-by-turn instructions from one address to another. This tool
                    provides you with a few different options for routes, both for driving and public transport.
                    2. Route-evaluating function to get the best routes out of all the different options.

                    Note that you MUST use the route-evaluating function to evaluate the routes, even if there are
                    less than three routes given. The route-evaluating function gives you explanations of why the
                    top routes were chosen. Use this explanation inside your reply to the user.
                    DO NOT give the turn-by-turn navigation directions to the user. Instead, you may give
                    a high-level overview of the route, describing it like a person familiar with the roads in Singapore.
                    State whether the route is based on public or private transport.
                    Example: "Take the route that goes along the AYE, as there is likely congestion on the PIE."
                    Another example: "You can take the usual route, but avoid Lornie Road as there has been an accident."

                    Reply the user in a friendly and conversational tone, maintaining a moderate level of formality.

                    You may use the formatting methods below to make your message easier to read.
                    Bold: *bold text*, Italics: _italicized text_, Underline: __underlined text__.
                    Do not use anything other than bold, italics, or underlines.

                    The chat history is below:
                    """,
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        # Combine all tools into a list
        route_eval_tool = self.get_route_eval_subllm(debug_mode)
        all_tools = [get_routes_tool, route_eval_tool]

        main_llm = ChatOpenAI(
            model_name="gpt-3.5-turbo-0125",
            # model_name="gpt-4-0613",
            openai_api_key=config["OPENAI_API_KEY"],
            temperature=0,
        )

        agent = create_openai_tools_agent(llm=main_llm, tools=all_tools, prompt=prompt)

        self.agent_executor = AgentExecutor(
            agent=agent, tools=all_tools, verbose=debug_mode
        )

    def get_route_eval_subllm(self, debug_mode):
        # Create sub-LLMs, each with their own prompts and toolkits
        subllm_route_evaluator = SubLLM(
            "RouteEvaluator",
            """
            Evaluate user-provided routes for usability and ease of use using available tools.

            Steps:
            1. Check road status for congestion and obstacles for each route.
            2. Find parking availability at destination.
            3. Score each route based on time, road conditions, and parking.
            4. Narrow down routes to 3 options using route ranking, including at least one public transport option.    

            Output should be the 3 route options from step 4.
            Provide reasoning for top 3 routes based on road works, incidents, parking availability, travel time, etc. If it is a public
            transport option, then you do not have to mention parking availability.
            """,
            [
                retrieve_incidents_tool,
                retrieve_parking_lots_tool,
                evaluate_route_tool,
                rank_routes_tool,
            ],
            verbose=debug_mode,
        )

        # Create tools from each sub-LLM
        # The "tool" is actually just asking the sub-LLM a question
        # We wrap sub-LLMs in tools to let the main LLM know how it can use the sub-LLMs
        subllm_route_evaluator_tool = StructuredTool.from_function(
            func=subllm_route_evaluator.query_agent,
            name="RouteEvaluator",
            description="""
            Use this tool to rank routes based on factors like time, road conditions, and parking availability.
            Provide input as 
            [
                {{
                    "routeIndex": routeOptionNumber,
                    "roads": [road1, road2, ...],
                    "destination": destination,
                    "isPublicTransport": boolean,
                    "estTravelTime": timeInMinutes,
                    "distance": distanceInKm,
                }},
                ...,
            ]
            Return the top three routes along with a brief explanation of the decision.""",
        )
        return subllm_route_evaluator_tool

    def query_agent(self, user_input, history):
        """
        History starts as a blank list, then gets populated with the user's chat history with the bot.
        Return both the answer and history, since history is stored inside the Telegram library in a user dictionary.
        """
        answer = self.agent_executor.invoke(
            {"input": user_input, "chat_history": history}
        )["output"]
        logger.info(f"Received output from primary agent: {answer}")
        history += [
            HumanMessage(content=user_input, example=False),
            AIMessage(content=answer, example=False),
        ]
        return answer, history


class SubLLM:
    def __init__(self, name, subprompt, tools, verbose=False):
        self.name = name
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    f""" 
                    You're a Singapore Land Transport Authority back office agent who does not directly interact with users.
                    {subprompt}
                    """,
                ),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        llm = ChatOpenAI(openai_api_key=config["OPENAI_API_KEY"], temperature=0)
        agent = create_openai_tools_agent(llm=llm, tools=tools, prompt=prompt)
        self.agent_executor = AgentExecutor(
            agent=agent, tools=tools, verbose=verbose, handle_parsing_errors=True
        )

    def query_agent(self, query) -> str:
        logger.info(f"Received {type(query)} input from primary agent: {query}")
        answer = self.agent_executor.invoke({"input": query})
        logger.info(f"Secondary agent generated output: {answer}")
        return answer


# THIS CODE BELOW IS FOR TESTING ONLY
if __name__ == "__main__":
    lc = LangchainInterface(debug_mode=True)
    history = []
    while user_input := input("Chat: "):
        ans, history = lc.query_agent(user_input, history)
        print("\nSmart Agent: " + ans + "\n")
    print("Chat done! History of chat:")
    print(history)
