import requests
import pandas as pd
import datetime
import os
from aws import AWS
from data_utils import upload_to_s3

class TrafficSpeedBands:
    """
    The module will download traffic speed bands from LTA data mall into the current working dir.
    Call download_all method with an output file name to append the data
    """

    def __init__(self, api_key):
        api_url = 'http://datamall2.mytransport.sg/ltaodataservice/v3/TrafficSpeedBands'
        headers = {'AccountKey': api_key}
        self.response = requests.get(api_url, headers=headers)
        self.s3 = AWS().s3

    def download_local(self, output_file='trafficspeedbands.csv'):
        total = len(self.response.json()["value"])
        timestamp = datetime.datetime.now()
        if total == 0:
            print('No data at the moment')
            return None

        linkid = []
        roadname = []
        speedband = []
        minimumspeed = []
        maximumspeed = []
        startlon = []
        startlat = []
        endlon = []
        endlat = []

        for i in range(0, total):
            linkid.append(self.response.json()["value"][i]["LinkID"])
            roadname.append(self.response.json()["value"][i]["RoadName"])
            speedband.append(self.response.json()["value"][i]["SpeedBand"])
            minimumspeed.append(self.response.json()["value"][i]["MinimumSpeed"])
            maximumspeed.append(self.response.json()["value"][i]["MaximumSpeed"])
            startlon.append(self.response.json()["value"][i]["StartLon"])
            startlat.append(self.response.json()["value"][i]["StartLat"])
            endlon.append(self.response.json()["value"][i]["EndLon"])
            endlat.append(self.response.json()["value"][i]["EndLat"])

        # Create a DataFrame with the extracted data
        data = pd.DataFrame({
            "linkid": linkid,
            "roadname": roadname,
            "speedband": speedband,
            "minimumspeed": minimumspeed,
            "maximumspeed": maximumspeed,
            "startlon": startlon,
            "startlat": startlat,
            "endlon": endlon,
            "endlat": endlat,
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

    def download_s3(self, output_file="trafficspeedbands.csv"):
        data = self.download_local(self, output_file)
        upload_to_s3('trafficspeedbands', data)
        return data