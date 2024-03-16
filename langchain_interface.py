import heapq
import os
import dotenv
import datetime
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

datamanager = DataManager()

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

        all_tools = [get_route_tool,
                     self.road_incidents_works_congestion_retrieval_function(),
                     self.parking_retrieval_function()]
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
                the road incidents, road works, or congestion at specified locations.
                To do so, you have tools that can query the database of LTA's transport/traffic-related data.

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
            query = f"""
                You have the following tools:
                1. ...
                2. ...
                
                Use these tools to get an overview of the road situation along the given route and provide an
                evaluation to the best of your ability.
                
                This is the given route: {locations}
                """
            riwc_agent = create_openai_tools_agent(self.llm, self.sql_toolkit.get_tools(), prompt)
            route_evaluation_tools = [...]  # TODO: Implement this
            agent_executor = AgentExecutor(agent=riwc_agent, tools=route_evaluation_tools, verbose=True)
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
                the availability of parking lots in a specified location.
                To do so, you have tools that can query the database of LTA's transport/traffic-related data.

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


class RouteInfoInput(BaseModel):
    route_str: str = Field(description='Route information string')

    def extract_incidents(self, roads_list: list[str]) -> str:
        """
        Given a list of roads, this function extracts and returns currently ongoing
        road incidents on these roads as a comma-separated list.
        
        :param: roads_list: the list of roads to extract traffic incidents for
        :returns: the number of traffic incidents currently ongoing on these roads
        """

        # run a query against our database to get traffic incidents for this road
        incidents = datamanager.query("SELECT * FROM trafficincidents WHERE (NOW() - INTERVAL '1 hour') <= timestamp")
        incidents = incidents[['type', 'message']]

        # extract the timestamp and filter to keep only incidents from less than 1 hour ago
        incidents[['timestamp', 'message']] = incidents['message'].split(' ', n=1, expand=True)
        incidents['timestamp'] = pd.to_datetime(incidents['timestamp'], format="(%d/%m)%H:%M")  # convert to time type
        one_hour_ago_today = datetime.datetime.now() - datetime.timedelta(hours=1)
        filtered_incidents = incidents[incidents['timestamp'] >= one_hour_ago_today]

        # join it into a single string since LLMs can read
        filtered_messages = ", ".join(list(filtered_incidents['message']))
        return filtered_messages

    def extract_parking_lots(self, destination: str) -> str:
        """
        Given a destination, gives the nearest car park and the available parking lots there as a string.

        :param: destination: the desired destination
        :return: information about the nearest car park and available parking lots there
        """
        # Retrieve car park data
        carpark_df = datamanager.query("SELECT * FROM carpark WHERE (NOW() - INTERVAL '2 hours') <= timestamp")
        lat, lon = ...  # TODO: get coordinates of destination

        # Calculate distance between destination and car parks
        carpark_df[["lat", "lon"]] = carpark_df["location"].str.split(" ", expand=True)
        carpark_df['distance'] = ((carpark_df["lat"] - lat) ** 2 + (carpark_df["lon"] - lon) ** 2) ** 0.5

        # Keep 3 nearest car parks and return them as a single string
        final_car_parks = carpark_df.sort_values('distance', ascending=False).iloc[:3]
        final_report = str(final_car_parks[["development", "availablelots"]])
        return final_report

    def evaluate_route(self, road_information: dict, carpark_availability: dict) -> float:
        """
        This tool evaluates a given route based on the incidents along the way and the parking lots available
        near the destination. Before using this tool, use extract_incidents and extract_parking_lots to get data
        about the incidents and parking lots for a particular route. Then, you will use that data for this tool.

        For the inputs to this tool, follow the following instructions.
        The data for the road_information dictionary comes from extract_incidents and should be formatted as follows:
        {
            "roadName": {
                "incidents": numberOfIncidents,
                "roadworks": numberOfRoadworks,
                "breakdowns": numberOfBreakdowns
            },
            "roadName2": ...,
        }
        The data for the carpark_availability dictionary comes from extract_parking_lots and should be formatted as
        follows:
        {
            "carpark": {
                "development": nameOfDevelopment,
                "availablelots": numberOfAvailableLots
            },
            "carpark2": ...,
        }
        The output of this function is a weighted score for the route, denoting its desirability and ease of use.

        :param road_information: a dictionary to be formatted as described above
        :param carpark_availability: a dictionary to be formatted as described above
        :return: a score for the route as described
        """

        # TODO: rewrite this part to match the format described above
        # input of routes: str for weight,
        time_weight = 0.6
        roadwork_weight = 0.1
        traffic_jam_weight = 0.4
        routes_with_score = []

        for route in routes:
            parsed_route, public_indicator = self.parse_route_info(route)
            time_score = parsed_route['estimated_time']
            # roadwork_score = -10 if parsed_route['roadwork'] else 0
            traffic_jam_score = -20 if parsed_route['traffic_jam'] else 0
            score = time_weight * time_score + traffic_jam_weight * traffic_jam_score
            routes_with_score.append((route, score, public_indicator))

        top_3_routes = self.get_top_transport_routes(routes_with_score)
        # return the top 3 routes with the lowest/highest score, ranked in a str. must have at least 1 public transport option
        # shape of the top_3_routes: list of 3 route tuples: (route_in_str_format, route_score, public_transport_indicator)
        return top_3_routes

    def get_top_transport_routes(self,
                                 routes_with_score: list[float],
                                 is_public_transport: list[bool],
                                 max_results=3) -> str:
        """
        TODO: Write out full explanation of this tool
        routes_with_score = [route1_score, route2_score, route3_score, ...]
        is_public_transport = [False, False, True, ...]
        """

        # get top 1 route of public transport
        public_routes = [route for route in routes_with_score if route[2] == 1]
        if public_routes:
            top_1_public_route = heapq.nlargest(1, public_routes, key=lambda x: x[1])
        else:
            top_1_public_route = None

        #get top 3 routes of all modes of transport
        top_3_routes = heapq.nlargest(max_results, routes_with_score, key=lambda x: x[1])

        #if there is no public transport in top3, add it in
        public_in_top_3 = any(route for route in top_3_routes if route[2] == 1)
        if not public_in_top_3 and top_1_public_route:
            top_3_routes[-1] = top_1_public_route # replace the last one with public route

        #sort the top routes to make sure it is desc
        top_routes = sorted(top_3_routes, key=lambda x: x[1], reverse = True)

        # Example output( in string format):
        """
        Best route is route 2 (score=9.7).
        Second best route is route 1 (score=6.7).
        Third best route is route 4 (score=5.5).
        """
        return top_routes


if __name__ == "__main__":
    lc = LangchainInterface(datamanager.connection_str)
    ans = lc.query_agent(
        "Is now a good time to drive from 259 Boon Lay Drive to Suntec City Mall?"
    )
    print(ans)
