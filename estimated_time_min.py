import requests
import pandas as pd
import datetime
import os
class EstimatedTravelTime:
    """
    The module will download estimated_travel_time from LTA data mall into the current working dir.
    Call download_all method with an output file name to append the data
    """
    def __init__(self, api_key='DZ4mqxgDSyqDNLVqkIMCog=='):
        api_url = 'http://datamall2.mytransport.sg/ltaodataservice/EstTravelTimes'
        headers = {'AccountKey': api_key}
        self.response = requests.get(api_url, headers=headers)

    def download_all(self, output_file='estimated_time_min.csv'):
        total = len(self.response.json()["value"])
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        name = []
        direction = []
        farendpoint = []
        startpoint = []
        endpoint = []
        est_min = []

        for i in range(0, total):
            name.append(self.response.json()["value"][i]["Name"])
            direction.append(self.response.json()["value"][i]["Direction"])
            farendpoint.append(self.response.json()["value"][i]["FarEndPoint"])
            startpoint.append(self.response.json()["value"][i]["StartPoint"])
            endpoint.append(self.response.json()["value"][i]["EndPoint"])
            est_min.append(self.response.json()["value"][i]["EstTime"])

        # Create a DataFrame with the extracted data
        data = pd.DataFrame({
            "Name": name,
            "Direction": direction,
            "FarEndPoint": farendpoint,
            "StartPoint": startpoint,
            "EndPoint": endpoint,
            "EstTime(Min)": est_min,
        })
        data['Timestamp'] = timestamp
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