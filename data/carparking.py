import requests
import pandas as pd
import datetime
import os


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

    def download_all(self, output_file="carparking.csv"):
        total = len(self.response.json()["value"])
        timestamp = datetime.datetime.now()
        # timestamp = now.strftime("%Y%m%d_%H%M%S")
        carpark_id = []
        area = []
        development = []
        location = []
        availablelots = []
        lottype = []
        agency = []

        for i in range(0, total):
            carpark_id.append(self.response.json()["value"][i]["CarParkID"])
            area.append(self.response.json()["value"][i]["Area"])
            development.append(self.response.json()["value"][i]["Development"])
            location.append(self.response.json()["value"][i]["Location"])
            availablelots.append(self.response.json()["value"][i]["AvailableLots"])
            lottype.append(self.response.json()["value"][i]["LotType"])
            agency.append(self.response.json()["value"][i]["Agency"])

        # Create a DataFrame with the extracted data
        data = pd.DataFrame(
            {
                "CarParkID": carpark_id,
                "Area": area,
                "Development": development,
                "Location": location,
                "AvailableLots": availablelots,
                "LotType": lottype,
                "Agency": agency,
            }
        )
        data["Timestamp"] = timestamp
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
