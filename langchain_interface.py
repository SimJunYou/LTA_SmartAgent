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


'''
Approach discussed yesterday:
extracted incidents info along the road and carpark info near destination, give score to them
compute weighted average of score based on ETA, incident, carpark, so we have a score for each route
rank and get the top 3 routes, with at least one public transport option


Approach discussed today:
similar to above with some modifications:
1. for public transport/ taxi, we do not need to compute/ use the carpark score, carpark score should be only computed for private transport
2. for car-owner, we will rank and give the top 2 private transport route and 1 public transport option as alternative when the 2 private routes are not feasible
   for non car-owners, we will rank and give the top 3 public transport route because private transport option is not relevant
   for non car-owners, we have discussed the possibility of taxi, but we think we do not need to analyse for taxi option, as the taxi driver will take care of that and we do not intend to include taxi driver as a user group
   
'''


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
        # lat, lon = ...  # TODO: get coordinates of destination # This can be done by using google map API to get the carparks then use LTA datamall to get the availability

        # Calculate distance between destination and car parks [replace by google map API]
        carpark_df[["lat", "lon"]] = carpark_df["location"].str.split(" ", expand=True)
        carpark_df['distance'] = ((carpark_df["lat"] - lat) ** 2 + (carpark_df["lon"] - lon) ** 2) ** 0.5

        # Keep 3 nearest car parks and return them as a single string
        final_car_parks = carpark_df.sort_values('distance', ascending=False).iloc[:3]
        final_report = str(final_car_parks[["development", "availablelots"]])
        return final_report

    def evaluate_route(self, time_taken, road_information: dict, private_or_public: bool,
                       carpark_availability: dict = None) -> float:
        """
        This tool evaluates a given route based on the incidents along the way and the parking lots available
        near the destination. Before using this tool, use extract_incidents and extract_parking_lots to get data
        about the incidents and parking lots for a particular route. Then, you will use that data for this tool.

        The time score is calculated based on the estimated time taken with a maximum time threshold.
        If the estimated time is less than the maximum, the score is proportionally reduced from the maximum score.
        If the estimated time exceeds the maximum threshold, the time score is set to 0.

        The road incident score starts at the maximum and is reduced by a fixed amount for each roadwork and a larger
        fixed amount for each breakdown or incident, with the minimum score being 0.

        The carpark score for private transport is determined by the number of available parking lots. If the total
        available lots exceed a predefined threshold, the score is set to the maximum. Otherwise, the score is
        proportionate to the number of available lots.

        For the inputs to this tool, follow the following instructions:
        - The data for the road_information dictionary comes from extract_incidents and should be formatted as follows:
          {
              "roadName": {
                  "incidents": numberOfIncidents,
                  "roadworks": numberOfRoadworks,
                  "breakdowns": numberOfBreakdowns
              },
              "roadName2": ...,
          }
        - The data for the carpark_availability dictionary comes from extract_parking_lots and should be formatted as
          follows:
          {
              "carpark": {
                  "development": nameOfDevelopment,
                  "availablelots": numberOfAvailableLots
              },
              "carpark2": ...,
          }
        - The private_or_public boolean indicates whether the route is a private transport option, it is True if private,
          otherwise False.

        The output of this function is a weighted score for the route, denoting its desirability and ease of use, out of 100.

        :param time_taken: an integer value representing the estimated time in minutes.
        :param road_information: a dictionary containing information about the road conditions as described.
        :param private_or_public: a boolean indicating whether the route is for private transport (True) or not (False).
        :param carpark_availability: an optional dictionary containing carpark availability information for private routes.
        :return: a score for the route, out of 100, indicating its desirability and ease of use.
        """

        # TODO: rewrite this part to match the format described above
        MAX_SCORE = 100
        MAX_TIME = 120
        MAX_CARPARK_LOTS = 100
        PENALTY_ROADWORK = 10
        PENALTY_INCIDENT = 20
        route_score = 0

        # Time score calculation
        if time_taken >= MAX_TIME:
            time_score = 0
        else:
            time_score = MAX_SCORE * (1 - (time_taken / MAX_TIME))

        # Incident and roadwork score calculation
        incident_score = MAX_SCORE
        for road in road_information.values():
            incident_score -= (road["roadworks"] * PENALTY_ROADWORK +
                               road["incidents"] * PENALTY_INCIDENT +
                               road["breakdowns"] * PENALTY_INCIDENT)
        incident_score = max(0, incident_score)

        # Carpark score calculation for private transport
        carpark_score = 0
        if private_or_public and carpark_availability is not None:
            total_lots = sum(carpark["availablelots"] for carpark in carpark_availability.values())
            carpark_score = MAX_SCORE if total_lots >= MAX_CARPARK_LOTS else total_lots / MAX_CARPARK_LOTS * MAX_SCORE

        # Weights and final score calculation
        if private_or_public:
            # For private transport, include carpark score in the final calculation
            time_weight = 0.5
            incident_weight = 0.2
            carpark_weight = 0.3
            route_score = (time_weight * time_score +
                           incident_weight * incident_score +
                           carpark_weight * carpark_score)
        else:
            # For public transport, only time and incident scores are considered
            time_weight = 0.7
            incident_weight = 0.3
            route_score = (time_weight * time_score +
                           incident_weight * incident_score)

        return route_score


    def get_top_public_transport_routes(self,
                                        routes_with_score: list[float],
                                        is_public_transport: list[bool]) -> str:
        """
        # this function is for non car-owners
        Get a string describing the top public transport routes based on their scores.


        :param routes_with_score (list of float): Scores for each route.
        :param is_public_transport (list of bool): Whether each route is a public transport route.
        :return: str: A formatted string describing the top public transport routes.
        """
        # Combine each route score with its index and filter for public transport
        public_routes_with_scores = [(index + 1, score) for index, (score, is_public) in
                                     enumerate(zip(routes_with_score, is_public_transport)) if is_public]

        # Sort the public transport routes by score in descending order
        sorted_public_routes = sorted(public_routes_with_scores, key=lambda x: x[1], reverse=True)

        # Create the formatted output for the top public transport routes
        top_route_strings = []
        route_descriptions = ["Best route", "Second best route", "Third best route"]
        for i, (route_index, score) in enumerate(sorted_public_routes[:3]):
            route_description = route_descriptions[i] if i < len(route_descriptions) else f"{i + 1}th best route"
            top_route_strings.append(f"{route_description} is route {route_index} (score={score:.1f})")

        # Join the route strings with a new line and appropriate heading
        if top_route_strings:
            return "For public transport options,\n" + ".\n".join(top_route_strings) + "."
        else:
            return "No public transport routes available."


    def get_top_transport_routes(routes_with_score: list[float],
                                 is_public_transport: list[bool]) -> str:
        """
        # this function is for car-owners
        Get a string describing the top 2 private transport routes and top 1 public transport route based on their scores.

        :param routes_with_score (list of float): Scores for each route.
        :param is_public_transport (list of bool): Whether each route is a public transport route.
        :return: str: A formatted string describing the top transport routes.
        """
        # Combine each route score with its index and separate public and private routes
        transport_routes_with_scores = [(index + 1, score, is_public) for index, (score, is_public) in
                                        enumerate(zip(routes_with_score, is_public_transport))]

        # Sort the transport routes by score in descending order
        sorted_transport_routes = sorted(transport_routes_with_scores, key=lambda x: x[1], reverse=True)

        # Split the sorted routes into public and private
        private_routes = [route for route in sorted_transport_routes if not route[2]]
        public_routes = [route for route in sorted_transport_routes if route[2]]

        # Create the formatted output
        top_route_strings = []

        # Get top 2 private routes
        for i, (route_index, score, _) in enumerate(private_routes[:2]):
            position = "Best" if i == 0 else "Second best"
            top_route_strings.append(f"{position} private route is route {route_index} (score={score:.1f})")

        # Get top 1 public route if available
        if public_routes:
            route_index, score, _ = public_routes[0]
            top_route_strings.append(f"Best public route is route {route_index} (score={score:.1f})")

        # Join the route strings with a new line and appropriate heading
        if top_route_strings:
            return "\n".join(top_route_strings) + "."
        else:
            return "No suitable transport routes available."


if __name__ == "__main__":
    lc = LangchainInterface(datamanager.connection_str)
    ans = lc.query_agent(
        "Is now a good time to drive from 259 Boon Lay Drive to Suntec City Mall?"
    )
    print(ans)
