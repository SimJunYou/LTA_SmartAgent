import requests
import pandas as pd
import datetime
import os
from aws import AWS
from data_utils import upload_to_s3

class RoadOpenings:
    """
    The module will download road openings from LTA data mall into the current working dir.
    Call download_all method with an output file name to append the data
    """
    def __init__(self, api_key):
        api_url = 'http://datamall2.mytransport.sg/ltaodataservice/RoadOpenings'
        headers = {'AccountKey': api_key}
        self.response = requests.get(api_url, headers=headers)
        self.s3 = AWS().s3

    def download_local(self, output_file='roadopenings.csv'):
        total = len(self.response.json()["value"])
        timestamp = datetime.datetime.now()
        if total == 0:
            print('No road opening at the moment')
            return None

        eventid = []
        startdate = []
        enddate = []
        svcdept = []
        roadname = []
        other = []

        for i in range(0, total):
            eventid.append(self.response.json()["value"][i]["EventID"])
            startdate.append(self.response.json()["value"][i]["StartDate"])
            enddate.append(self.response.json()["value"][i]["EndDate"])
            svcdept.append(self.response.json()["value"][i]["SvcDept"])
            roadname.append(self.response.json()["value"][i]["RoadName"])
            other.append(self.response.json()["value"][i]["Other"])

        # Create a DataFrame with the extracted data
        data = pd.DataFrame({
            "eventid": eventid,
            "startdate": startdate,
            "enddate": enddate,
            "svcdept": svcdept,
            "roadname": roadname,
            "other": other,
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
    def download_s3(self, output_file="roadopenings.csv"):
        data = self.download_local(output_file)
        upload_to_s3('roadopenings', data)
        return data
