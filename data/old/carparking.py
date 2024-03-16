import requests
import pandas as pd
import datetime
import os
from aws import AWS
from data.data_utils import upload_to_s3


class CarPark:
    """
    The module will download car parking availability from LTA data mall into the current working dir.
    Call download_all method with an output file name to append the data
    """

    def __init__(self, api_key):
        api_url = (
            "http://datamall2.mytransport.sg/ltaodataservice/CarParkAvailabilityv2"
        )
        headers = {"AccountKey": api_key}
        self.response = requests.get(api_url, headers=headers)
        self.s3 = AWS().s3

    def download_local(self, output_file="carpark.csv"):
        total = len(self.response.json()["value"])
        carparkid = []
        area = []
        development = []
        location = []
        availablelots = []
        lottype = []
        agency = []
        timestamp = datetime.datetime.now()

        for i in range(0, total):
            carparkid.append(self.response.json()["value"][i]["CarParkID"])
            area.append(self.response.json()["value"][i]["Area"])
            development.append(self.response.json()["value"][i]["Development"])
            location.append(self.response.json()["value"][i]["Location"])
            availablelots.append(self.response.json()["value"][i]["AvailableLots"])
            lottype.append(self.response.json()["value"][i]["LotType"])
            agency.append(self.response.json()["value"][i]["Agency"])

        # Create a DataFrame with the extracted data
        data = pd.DataFrame(
            {
                "carparkid": carparkid,
                "area": area,
                "development": development,
                "location": location,
                "availablelots": availablelots,
                "lottype": lottype,
                "agency": agency,
            }
        )
        data["timestamp"] = timestamp
        print("Download all completed, updating to", output_file)
        # Check if the file exists
        if os.path.exists(output_file):
            # File exists, append to it
            print("Appending to existing", output_file)
            data.to_csv(output_file, mode="a", header=False, index=False)
        else:
            # File does not exist, create a new one
            print("Creating new", output_file)
            data.to_csv(output_file, index=False)
        return data

    def download_s3(self, output_file="carpark.csv"):
        data = self.download_local(output_file)
        upload_to_s3("carpark", data)
        return data
