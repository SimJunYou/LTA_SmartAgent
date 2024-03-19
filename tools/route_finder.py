import datetime
from urllib.parse import urlencode
import requests
from bs4 import BeautifulSoup
import dotenv

from langchain_core.tools import StructuredTool


config = dotenv.dotenv_values(".env")


def get_routes(origin: str, destination: str):
    # TODO: Use "avoid" parameter
    nav = Navigation(origin, destination, config["GOOGLE_API_KEY"])
    return nav.driving() + nav.publictransport()

get_routes_tool = StructuredTool.from_function(
    func=get_routes,
    name="RouteFindingTool",
    description="""
    Given address 1 and address 2, returns the possible routes between them in a single string of turn-by-turn directions.
    First, a few options for driving (private transport) will be given. Then, a few options for public transport will be given.

    For both private and public transport, route options will start with the following line:
    "Option [optionNumber] takes [numMinutes] mins and is [distanceInKm] km long!"
    These should be noted for later use in other tools.

    Some portions of the directions may include road and expressway names, which should be noted and used.
    """
)


class Navigation:
    """
    The module will provide the steps to go from origin point to end point
    origin and end point must be a text string consisting of
    a) 'start_lat,start_lon'
    b) address such as '853 Hougang Central'
    c) Postal code

    The module can process a list of things to avoid (avoid = ['pizza', 'tolls', 'police'])

    The module will provide response with multiple transport modes such as driving, walking, bicycling, transit (public transport)

    """

    def __init__(
        self,
        origin,
        destination,
        google_api_key,
        alternatives=True,
        avoid=[],
    ):
        self.alternatives = alternatives
        avoid_list_const = ["tolls", "highways", "ferries", "indoor"]
        avoid_list = []

        for thing_to_avoid in avoid:
            if thing_to_avoid in avoid_list_const:
                avoid_list.append(thing_to_avoid)

        self.avoid_str = "|".join(avoid_list)
        self.google_api_key = google_api_key

        timestamp = datetime.datetime.now()
        timestamp_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        self.output_file = f"navigation-{timestamp_str}.txt"
        self.origin = origin
        self.destination = destination
        self.validate_address()

    def validate_address(self):
        verified_origin = self.text_query(self.origin)
        verified_destination = self.text_query(self.destination)

        if len(verified_origin) > 1:
            print("There are more than 1 place matching your original location")
            print(location for location in verified_origin)

        else:
            self.origin = verified_origin[0]

        if len(verified_destination) > 1:
            print("There are more than 1 place matching your destination location")
            print(location for location in verified_destination)
        else:
            self.destination = verified_destination[0]

    def text_query(self, query):
        url = "https://places.googleapis.com/v1/places:searchText"
        params = {"textQuery": query}
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.google_api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress",  # ,places.priceLevel"
        }

        response = requests.post(url, json=params, headers=headers)

        return [place["formattedAddress"] for place in response.json()["places"]]

    def query(self, params):
        query_string = urlencode(params)

        # Construct the complete URL
        base_url = "https://maps.googleapis.com/maps/api/directions/json?"
        url = base_url + query_string
        return requests.request("Get", url)

    def parse_response(self, response):
        clean_steps = []
        total_distance = []
        total_duration = []

        options = len(response.json()["routes"])
        output_str = ""
        if options > 0:
            output_str += f"There are {options} options to go there:\n"

            for k in range(0, options):
                steps = []
                for i in range(
                    0, len(response.json()["routes"][k]["legs"][0]["steps"])
                ):
                    steps.append(
                        response.json()["routes"][k]["legs"][0]["steps"][i][
                            "html_instructions"
                        ]
                    )
                clean_steps.append(
                    [
                        BeautifulSoup(step, "html.parser").get_text().strip()
                        for step in steps
                    ]
                )
                total_distance.append(
                    response.json()["routes"][k]["legs"][0]["distance"]["text"]
                )
                total_duration.append(
                    response.json()["routes"][k]["legs"][0]["duration"]["text"]
                )

            # with open(self.output_file, "a") as file:
            for k in range(0, options):
                newline = f"Option {k+1} takes {total_duration[k]} and is {total_distance[k]} long!"
                # file.writelines([newline, '\n'])
                output_str += newline + "\n"
                for line in clean_steps[k]:
                    # file.writelines(line + '\n')
                    output_str += line + "\n"
                # file.writelines(['\n', '\n'])
                output_str += "\n\n"

            # print('Navigation steps written successfully to', self.output_file)

        else:
            return "Exact address not found, please try again."

        return output_str

    def driving(self):
        mode = "driving"
        params_driving = {
            "origin": self.origin,
            "destination": self.destination,
            "alternatives": self.alternatives,
            "mode": mode,
            "avoid": self.avoid_str,
            "key": self.google_api_key,
        }
        # self.write_to_file(self.query(params_driving))
        return "By private transport, " + self.parse_response(
            self.query(params_driving)
        )

    def publictransport(self):
        mode = "transit"
        params_public = {
            "origin": self.origin,
            "destination": self.destination,
            "alternatives": self.alternatives,
            "mode": mode,
            "avoid": self.avoid_str,
            "key": self.google_api_key,
        }
        # self.write_to_file(self.query(params_public))
        return "By public transport, " + self.parse_response(self.query(params_public))


# Here is how to test this function
# origin = "NUS LT15"
# destination = "Fairmont hotel"  # I select this one because by default the API will not recognize it
# avoid = ["pizza", "tolls", "police"]
# test = Navigation(
#     origin,
#     destination,
#     alternatives="true",
#     avoid=avoid,
#     google_api_key=config["GOOGLE_API_KEY"],
# )

# Check if the address has been converted automatically to a valid one
# test.origin
# test.destination
# Create navigation routes with driving mode
# print(test.driving() + test.publictransport())
# Create navigation routes with public transportation mode
# The output is written to a text file

# For free text search, try this
# print(test.text_query("parking near" + test.destination))
