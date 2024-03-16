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

from langchain.tools import StructuredTool


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
        self.sql_toolkit = sql_toolkit
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
                2. A function that can query the database of LTA's transport/traffic-related data for road incidents, road works, or congestion.
                3. A function that can query the database of LTA's transport/traffic-related data for parking lot availabilities.

                Follow these steps:
                1. Use the route-finding function to get a route between the user's desired source and destination
                2. Based on the turn-by-turn directions, use function 2 to find out whether there will be any congestion or obstacles
                at each road from the route in step 1, not only the source and destination.
                3. Use function 3 to find out the number of available parking lots at the end.

                Assume that the mode of transport is driving, and advise users on whether or not to drive to the location based off the response of the 3 functions.
                You should always check the turn-by-turn instructions and report whether there are road incidents, road works, or congestion. You may advise users
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

        all_tools = [get_route_tool, self.road_incidents_works_congestion_retrieval_function(), self.parking_retrieval_function()]
        agent = create_openai_tools_agent(self.llm, all_tools, prompt)
        self.agent_executor = AgentExecutor(agent=agent, tools=all_tools, verbose=True)

    def query_agent(self, query):
        answer = self.agent_executor.invoke({"input": query})["output"]
        # answer = self.agent.invoke({"input": query})
        # chain = prompt | agent
        # answer = chain.invoke({"input": "Which area has the most available lots?"})
        return answer

    def road_incidents_works_congestion_retrieval_function(self):
        """
        This function will help you find the road incidents, road works, or congestion at specified locations.
        :return: road incidents, road works, or congestion at location
        """
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                You are a Singapore Land Transport Authority agent. You have been tasked with answering queries regarding
                the aroad incidents, road works, or congestion at specified locations. To do so, you have tools that can query the database of LTA's transport/traffic-related data.

                Below is such a query:
                """,
                ),
                ("user", "{input}"),
                AIMessage(content=SQL_FUNCTIONS_SUFFIX),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )
        prompt = prompt.partial(
            **self.sql_toolkit.get_context()
        )  # fill in part of the prompt from the sql_toolkit context

        def get_riwc(locations: str) -> str:
            query = f"""get the road incidents, road works, or congestion at multiple {locations} from the database.
                Find the most recent timestamp to the item you're looking for in the database.
                """
            riwc_agent = create_openai_tools_agent(self.llm, self.sql_toolkit.get_tools(), prompt)
            agent_executor = AgentExecutor(agent=riwc_agent, tools=self.sql_toolkit.get_tools(), verbose=True)
            result = agent_executor.invoke({"input": query})["output"]
            return result

        riwc_tool = StructuredTool.from_function(func=get_riwc,
                                                description='This function will help you get the road incidents, road works, or congestion at specified locations.')

        return riwc_tool
    
    def parking_retrieval_function(self):
        """
        This function will help you find the number of parking lots at a specified location.
        :return: number of lots
        """
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                You are a Singapore Land Transport Authority agent. You have been tasked with answering queries regarding
                the availability of parking lots in a specified location. To do so, you have tools that can query the database of LTA's transport/traffic-related data.

                Below is such a query:
                """,
                ),
                ("user", "{input}"),
                AIMessage(content=SQL_FUNCTIONS_SUFFIX),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )
        prompt = prompt.partial(
            **self.sql_toolkit.get_context()
        )  # fill in part of the prompt from the sql_toolkit context

        def get_parking(location: str) -> str:
            query = f"""get the number of available parking lots at {location} from the database.
                Find the most recent timestamp to the item you're looking for in the database.
                """
            parking_agent = create_openai_tools_agent(self.llm, self.sql_toolkit.get_tools(), prompt)
            agent_executor = AgentExecutor(agent=parking_agent, tools=self.sql_toolkit.get_tools(), verbose=True)
            result = agent_executor.invoke({"input": query})["output"]
            return result

        parking_tool = StructuredTool.from_function(func=get_parking,
                                                description='This function will help you get the number of available lots at a specified location.')

        return parking_tool


if __name__ == "__main__":
    dm = DataManager()
    lc = LangchainInterface(dm.connection_str)
    ans = lc.query_agent(
        "Is now a good time to drive from 259 Boon Lay Drive to Suntec City Mall?"
    )
    print(ans)
