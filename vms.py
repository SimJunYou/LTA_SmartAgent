import requests
import pandas as pd
import datetime
import os


class VMS:
    """
    The module will download traffic speed bands from LTA data mall into the current working dir.
    Call download_all method with an output file name to append the data
    """

    def __init__(self, api_key):
        api_url = 'http://datamall2.mytransport.sg/ltaodataservice/VMS'
        headers = {'AccountKey': api_key}
        self.response = requests.get(api_url, headers=headers)

    def download_all(self, output_file='data.csv'):
        total = len(self.response.json()["value"])
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        if total == 0:
            print('No data at the moment')
            return None

        equiment_id = []
        lat = []
        lon = []
        message = []

        for i in range(0, total):
            equiment_id.append(self.response.json()["value"][i]["EquipmentID"])
            lat.append(self.response.json()["value"][i]["Latitude"])
            lon.append(self.response.json()["value"][i]["Longitude"])
            message.append(self.response.json()["value"][i]["Message"])

        # Create a DataFrame with the extracted data
        data = pd.DataFrame({
            "EquipmentID": equiment_id,
            "Latitude": lat,
            "Longitude": lon,
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
