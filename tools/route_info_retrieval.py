import datetime

import pandas as pd
from langchain.tools import StructuredTool

from data_manager import data_manager
from tools.router import get_addr_coordinates


def retrieve_incidents(roads_list: str) -> str:
    # somehow the LLM just wants to call this tool in this format...
    roads_list = roads_list.split(", ")

    # run a query against our database to get traffic incidents for this road
    incidents = data_manager().query(
        "SELECT * FROM trafficincidents WHERE (NOW() - INTERVAL '1 hour') <= timestamp"
        # "SELECT * FROM trafficincidents"
    )

    incidents = incidents[["type", "message"]]

    # extract the timestamp and filter to keep only incidents from less than 1 hour ago
    incidents[["timestamp", "message"]] = incidents["message"].str.split(
        " ", n=1, expand=True
    )
    incidents["timestamp"] = pd.to_datetime(
        incidents["timestamp"], format="(%d/%m)%H:%M"
    )  # convert to time type
    one_hour_ago_today = datetime.datetime.now() - datetime.timedelta(hours=1)
    filtered_incidents = incidents[incidents["timestamp"] >= one_hour_ago_today]

    # join it into a single string since LLMs can read
    filtered_messages = ", ".join(list(filtered_incidents["message"]))
    return filtered_messages


def retrieve_parking_lots(destination: str) -> str:
    # Retrieve car park data
    carpark_df = data_manager().query(
        "SELECT * FROM carpark WHERE (NOW() - INTERVAL '1 hours') <= timestamp"
    )
    lat, lon = map(float, get_addr_coordinates(destination).split(","))
    # TODO: Think about converting this to use Google Maps instead

    # Calculate distance between destination and car parks [replace by google map API]
    carpark_df[["lat", "lon"]] = carpark_df["location"].str.split(" ", expand=True)
    carpark_df["distance"] = (
        (pd.to_numeric(carpark_df["lat"]) - lat) ** 2
        + (pd.to_numeric(carpark_df["lon"]) - lon) ** 2
    ) ** 0.5

    # Keep 3 nearest car parks and return them as a single string
    final_car_parks = carpark_df.sort_values("distance", ascending=False).iloc[:3]
    final_report = str(final_car_parks[["development", "availablelots"]])
    return final_report


retrieve_incidents_tool = StructuredTool.from_function(
    func=retrieve_incidents,
    name="IncidentRetrieverTool",
    description="""
    Extract and return currently ongoing road incidents on the provided roads as a comma-separated list.
    Expected input: "Boon Lay Dr, Boon Lay Wy, ..."
    """,
)

retrieve_parking_lots_tool = StructuredTool.from_function(
    func=retrieve_parking_lots,
    name="ParkingAvailabilityRetrieverTool",
    description="""
    Given a destination, gives the nearest car park and the available parking lots there as a string.
    """,
)
