import requests
import pandas as pd
import datetime
import os
from aws import AWS
from data_utils import upload_to_s3

class EstimatedTravelTime:
    """
    The module will download estimated_travel_time from LTA data mall into the current working dir.
    Call download_all method with an output file name to append the data
    """
    def __init__(self, api_key):
        api_url = 'http://datamall2.mytransport.sg/ltaodataservice/EstTravelTimes'
        headers = {'AccountKey': api_key}
        self.response = requests.get(api_url, headers=headers)
        self.s3 = AWS().s3

    def download_local(self, output_file='esttraveltimes.csv'):
        total = len(self.response.json()["value"])
        name = []
        direction = []
        farendpoint = []
        startpoint = []
        endpoint = []
        esttime = []
        timestamp = datetime.datetime.now()

        for i in range(0, total):
            name.append(self.response.json()["value"][i]["Name"])
            direction.append(self.response.json()["value"][i]["Direction"])
            farendpoint.append(self.response.json()["value"][i]["FarEndPoint"])
            startpoint.append(self.response.json()["value"][i]["StartPoint"])
            endpoint.append(self.response.json()["value"][i]["EndPoint"])
            esttime.append(self.response.json()["value"][i]["EstTime"])

        # Create a DataFrame with the extracted data
        data = pd.DataFrame({
            "name": name,
            "direction": direction,
            "farendpoint": farendpoint,
            "startpoint": startpoint,
            "endpoint": endpoint,
            "esttime": esttime,
        })
        data['timestamp'] = timestamp
        print('Download all completed, updating to', output_file)
        # Check if the file exists
        if os.path.exists(output_file):
            # File exists, append to it
            print("Appending to existing", output_file)
            data.to_csv(output_file, mode='a', header=False, index=False)
        else:
            # File does not exist, create a new one
            print("Creating new", output_file)
            data.to_csv(output_file, index=False)
        return data

    def download_s3(self, output_file="esttraveltimes.csv"):
        data = self.download_local(self, output_file)
        upload_to_s3('esttraveltimes', data)
        return data