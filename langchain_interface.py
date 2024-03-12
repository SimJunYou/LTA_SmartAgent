import os
import dotenv
import pandas as pd

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.globals import set_debug

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.prompt import SQL_FUNCTIONS_SUFFIX
from langchain_community.utilities import SQLDatabase

from langchain_openai import ChatOpenAI


from data_manager import DataManager
from tools.router import get_route_tool

config = dotenv.dotenv_values(".env")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

set_debug(False)


class LangchainInterface:
    def __init__(self, connection_str):
        self.llm = ChatOpenAI(openai_api_key=config["OPENAI_API_KEY"], temperature=0)

        db = SQLDatabase.from_uri(connection_str)

        # Part below is from the following doc:
        # https://python.langchain.com/docs/integrations/toolkits/sql_database
        sql_toolkit = SQLDatabaseToolkit(db=db, llm=self.llm)
        context = sql_toolkit.get_context()
        tools = sql_toolkit.get_tools()

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                You are a Singapore Land Transport Authority agent. You have been tasked with answering queries regarding
                the best mode of transport from point A to point B. To do so, you have the following tools:
                1. A route-finding function that you can call to give you the turn-by-turn instructions from any address 
                in Singapore to any other address.
                2. A database of LTA's transport/traffic-related data. The schema will be described later.

                Follow these steps:
                1. Use the route-finding function to get a route between the user's desired source and destination
                2. Based on the turn-by-turn directions, figure out whether there will be any congestion or obstacles
                along the way, and also whether there will be available parking lots at the end. To achieve this,
                filter the relevant tables by the specific roads mentioned in the directions.

                Assume that the mode of transport is driving, and advise users on whether or not to drive to the location.
                You should always report whether there are road incidents, road works, or congestion. You may advise users
                to take alternate routes if there are issues with any of the roads on the way.
                If there are zero nearby parking lots, then driving is never advised.
                If your opinion is that driving is not advised, then inform the user to take public transport instead.

                You DO NOT NEED to provide turn-by-turn instructions, nor provide exact travel time estimates.
                NEVER run SELECT statements without a WHERE condition.
                Try to limit the number of SQL queries made to the best of your ability.
                
                Below is such a query:
                """,
                ),
                ("user", "{input}"),
                AIMessage(content=SQL_FUNCTIONS_SUFFIX),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )
        prompt = prompt.partial(
            **context
        )  # fill in part of the prompt from the sql_toolkit context

        all_tools = [get_route_tool] + sql_toolkit.get_tools()
        agent = create_openai_tools_agent(self.llm, all_tools, prompt)
        self.agent_executor = AgentExecutor(agent=agent, tools=all_tools, verbose=True)

    def query_agent(self, query):
        answer = self.agent_executor.invoke({"input": query})["output"]
        # answer = self.agent.invoke({"input": query})
        # chain = prompt | agent
        # answer = chain.invoke({"input": "Which area has the most available lots?"})
        return answer


if __name__ == "__main__":
    dm = DataManager()
    lc = LangchainInterface(dm.connection_str)
    ans = lc.query_agent(
        "Is now a good time to drive from 259 Boon Lay Drive to Suntec City Mall?"
    )
    print(ans)
