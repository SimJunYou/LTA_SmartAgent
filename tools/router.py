import requests
import dotenv
import json
from bs4 import BeautifulSoup
from urllib.parse import urlencode

from langchain_core.tools import tool

config = dotenv.dotenv_values(".env")


@tool
def get_route_tool(addr1: str, addr2: str) -> str:
    """
    Given address 1 and address 2, returns the route between them in a single string of turn-by-turn directions.
    Some portions of the directions may include road and expressway names, which should be noted and used.
    """
    return Router().get_route(addr1, addr2)


def get_addr_coordinates(addr: str) -> str:
    return Router().get_addr_coords(addr)


class Router:
    def __init__(self):
        self.api_key = config["GOOGLE_API_KEY"]
        self.onemap_api_url = "https://www.onemap.gov.sg/api/common/elastic/search?"
        self.gmaps_api_url = "https://maps.googleapis.com/maps/api/directions/json?"

    def get_route(self, start_addr, end_addr):
        print("Starting to find route...")
        start_coords = self.get_addr_coords(start_addr)
        end_coords = self.get_addr_coords(end_addr)
        directions = self.call_route_api(start_coords, end_coords)
        print("Found it!")
        return directions

    def get_addr_coords(self, search):
        search.replace(" ", "%20")  # encode spaces in query
        api_search = f"searchVal={search}&returnGeom=Y&getAddrDetails=N"

        response = requests.get(self.onemap_api_url + api_search)
        results = json.loads(response.text)["results"]
        if len(results) == 0:
            raise (f"Could not find location: {search}")

        first_result = results[0]
        lat = first_result["LATITUDE"]
        lon = first_result["LONGITUDE"]
        coords = lat + "," + lon
        return coords

    def call_route_api(self, start_coords, end_coords):
        """
        start_coords and end_coords are comma-separated lat-lon coordinate strings
        """
        params = {
            "origin": start_coords,
            "destination": end_coords,
            "key": self.api_key,
        }
        query_string = urlencode(params)

        # Construct the complete URL
        url = self.gmaps_api_url + query_string
        response = requests.request("Get", url)

        steps = []
        for i in range(0, len(response.json()["routes"][0]["legs"][0]["steps"])):
            steps.append(
                response.json()["routes"][0]["legs"][0]["steps"][i]["html_instructions"]
            )

        clean_steps = [
            BeautifulSoup(step, "html.parser").get_text().strip() for step in steps
        ]

        step_string = "\n".join(clean_steps)

        return step_string
