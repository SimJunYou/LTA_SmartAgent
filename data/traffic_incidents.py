import requests
import pandas as pd
import datetime
import os


class TrafficIncidents:
    """
    The module will download traffic incidents from LTA data mall into the current working dir.
    Call download_all method with an output file name to append the data
    """

    def __init__(self, api_key):
        api_url = 'http://datamall2.mytransport.sg/ltaodataservice/TrafficIncidents'
        headers = {'AccountKey': api_key}
        self.response = requests.get(api_url, headers=headers)

    def download_all(self, output_file='traffic_incidents.csv'):
        total = len(self.response.json()["value"])
        timestamp = datetime.datetime.now()
        if total == 0:
            print('No road opening at the moment')
            return None

        event_type = []
        latitude = []
        longitude = []
        message = []

        for i in range(0, total):
            event_type.append(self.response.json()["value"][i]["Type"])
            latitude.append(self.response.json()["value"][i]["Latitude"])
            longitude.append(self.response.json()["value"][i]["Longitude"])
            message.append(self.response.json()["value"][i]["Message"])

        # Create a DataFrame with the extracted data
        data = pd.DataFrame({
            "Type": event_type,
            "Latitude": latitude,
            "Longitude": longitude,
            "Message": message,
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
