import os
import requests
import json
import datetime

import pandas as pd


class DatamallInterface:
    """
    Simple interface for the LTA Datamall API. Using a mapping of table names to
    corresponding API URLs, we only need the table name to call the appropriate
    API. To add new Datamall APIs, change the code in this interface.
    """

    def __init__(self, api_key):
        self.headers = {"AccountKey": api_key}
        self.base_url = "http://datamall2.mytransport.sg/ltaodataservice/"
        self.api_urls = {
            "carpark": "CarParkAvailabilityv2",
            "erprates": "ERPRates",
            "esttraveltimes": "EstTravelTimes",
            "faultytrafficlights": "FaultyTrafficLights",
            "roadopenings": "RoadOpenings",
            "roadworks": "RoadWorks",
            "trafficincidents": "TrafficIncidents",
            "trafficspeedbands": "v3/TrafficSpeedBands",
            "trafficimages": "Traffic-Imagesv2",
            "vms": "VMS",
        }  # the keys here are the corresponding table names in the database

    def call(self, api_name):
        """
        Saves data from a Datamall API call to a Pandas DataFrame and returns it.

        :param api_name: the name of the API to be called
        :param output_file: the name of the CSV file to save the data to
        :returns: dataframe of API response data
        :raises HTTPError: if API call fails
        """
        api_url = self.base_url + self.api_urls[api_name]
        response = requests.get(api_url, headers=self.headers)

        # check success of API call to avoid bad data
        if response.status_code != 200:
            raise requests.exceptions.HTTPError("Did not get status 200 from response")

        # our tables are in the same schema as the response data
        # directly convert to a dataframe using pd.DataFrame.from_records
        res_val = json.loads(response.text)["value"]
        data = pd.DataFrame.from_records(res_val)

        # make columns lowercase to match schema in our database
        data.columns = [col.lower() for col in data.columns]
        data["timestamp"] = datetime.datetime.now()
        return data

    def download_local(self, api_name, output_file):
        """
        Saves data from a Datamall API call to a CSV file.

        :param api_name: the name of the API to be called
        :param output_file: the name of the CSV file to save the data to
        """
        data = self.call(api_name)
        print("Download completed, updating to", output_file)
        # Check if the file exists
        if os.path.exists(output_file):
            # File exists, append to it
            print("Appending to existing", output_file)
            data.to_csv(output_file, mode="a", header=False, index=False)
        else:
            # File does not exist, create a new one
            print("Creating new", output_file)
            data.to_csv(output_file, index=False)

    # def download_s3(self, output_file="carpark.csv"):
    #     data = self.download_local(output_file)
    #     upload_to_s3("carpark", data)
    #     return data
