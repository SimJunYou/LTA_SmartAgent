import os
import dotenv
import datetime
import pandas as pd

from langchain.agents import AgentExecutor, create_openai_tools_agent, ZeroShotAgent
from langchain.chains import LLMChain
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.prompts.chat import (
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.prompt import SQL_FUNCTIONS_SUFFIX
from langchain_community.utilities import SQLDatabase
from langchain.globals import set_debug
from langchain_openai import ChatOpenAI
from langchain.agents.openai_assistant import OpenAIAssistantRunnable
from langchain.memory import ConversationBufferMemory
from langchain.tools import StructuredTool

from data_manager import data_manager
from custom_logger import logger

# TODO: Merge router into navigation
from tools.router import get_addr_coordinates
from tools.route_finder import get_routes_tool
from tools.route_info_retrieval import retrieve_incidents, retrieve_parking_lots
from tools.route_evaluation import (
    evaluate_route,
    get_top_public_transport_routes,
    get_top_transport_routes,
)

config = dotenv.dotenv_values(".env")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

set_debug(False)


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

        main_llm = ChatOpenAI(openai_api_key=config["OPENAI_API_KEY"], temperature=0)

        agent = create_openai_tools_agent(llm=main_llm, tools=all_tools, prompt=prompt)

        self.agent_executor = AgentExecutor(
            agent=agent, tools=all_tools, verbose=debug_mode
        )

    def get_route_eval_subllm(self, debug_mode):
        # Create sub-LLMs, each with their own prompts and toolkits
        subllm_route_evaluator = SubLLM(
            "RouteEvaluator",
            """
            Evaluate user-provided routes for usability and ease of use using:
            1. Road status function for road incidents, road works, and congestion.
                - The input format for this function is a single string of road names, comma-separated
                - E.g., "Boon Lay Dr, Boon Lay Wy, ..."
            2. Parking function for destination parking availability.
            3. Route evaluation function for scoring based on time, road conditions, and parking.
            4. Route ranking function - identifies top 2 private and top 1 public transport routes.

            The user's input will be a list of route dictionaries in the following format:
            [
                \{
                    "routeIndex": indexNumberOfRoute,
                    "roads": [road1, road2, ...],
                    "destination": destination,
                    "isPublicTransport": boolean,
                    "estTravelTime": timeInMinutes,
                    "distance": distanceInKm,
                \},
                ...,
            ]


            Steps:
            1. Check road status for congestion and obstacles for each route.
            2. Find parking availability at destination.                
            3. Score each route based on time, road conditions, and parking.
            4. Narrow down routes to 3 options using route ranking, including at least one public transport option.

            If there are 3 or fewer options available, then skip steps 3 and 4.
            Output should be the 3 route options from step 4.
            Provide reasoning for top 3 routes based on road works, incidents, parking availability, travel time, etc.
            """,
            [retrieve_incidents, retrieve_parking_lots, get_routes_tool],
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
            Extract roads from turn-by-turn navigations and list them as strings under the "roads" key in each route dictionary.
            Use the option number from turn-by-turn directions as the route index. Preserve the original destination provided by the user.
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

    def query_agent(self, query):
        logger.info(f"Received input from primary agent: {query}")
        try:
            answer = self.agent_executor.invoke({"input": query})
        except Exception as e:
            logger.error(f"Error in secondary agent {self.name}!\n{type(e)}: {e}")
            error_msg = f"Calling tool with arguments: {query} raised the following error:\n\n{type(e)}: {e}\n"
            error_msg += "Try calling the tool again with different arguments. Follow the input format instructions."
            return error_msg
        logger.info(f"Secondary agent generated output: {answer}")
        return answer


# THIS CODE BELOW IS FOR TESTING ONLY
if __name__ == "__main__":
    lc = LangchainInterface(debug_mode=False)
    # ans = lc.query_agent(
    #     "How should I get from 259 Boon Lay Drive to Suntec City Mall?"
    # )
    history = []
    while user_input := input("Chat: "):
        ans, history = lc.query_agent(user_input, history)
        print("\nSmart Agent: " + ans + "\n")
    print("Chat done! History of chat:")
    print(history)
