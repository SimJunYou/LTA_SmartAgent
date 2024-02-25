import requests
import pandas as pd
import datetime
import os


class TrafficSpeedBands:
    """
    The module will download traffic speed bands from LTA data mall into the current working dir.
    Call download_all method with an output file name to append the data
    """

    def __init__(self, api_key='DZ4mqxgDSyqDNLVqkIMCog=='):
        api_url = 'http://datamall2.mytransport.sg/ltaodataservice/v3/TrafficSpeedBands'
        headers = {'AccountKey': api_key}
        self.response = requests.get(api_url, headers=headers)

    def download_all(self, output_file='data.csv'):
        total = len(self.response.json()["value"])
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        if total == 0:
            print('No data at the moment')
            return None

        link_id = []
        road_name = []
        speedband = []
        minspeed = []
        maxspeed = []
        start_lon = []
        start_lat = []
        end_lon = []
        end_lat = []

        for i in range(0, total):
            link_id.append(self.response.json()["value"][i]["LinkID"])
            road_name.append(self.response.json()["value"][i]["RoadName"])
            speedband.append(self.response.json()["value"][i]["SpeedBand"])
            minspeed.append(self.response.json()["value"][i]["MinimumSpeed"])
            maxspeed.append(self.response.json()["value"][i]["MaximumSpeed"])
            start_lon.append(self.response.json()["value"][i]["StartLon"])
            start_lat.append(self.response.json()["value"][i]["StartLat"])
            end_lon.append(self.response.json()["value"][i]["EndLon"])
            end_lat.append(self.response.json()["value"][i]["EndLat"])

        # Create a DataFrame with the extracted data
        data = pd.DataFrame({
            "LinkID": link_id,
            "RoadName": road_name,
            "SpeedBand": speedband,
            "MinimumSpeed": minspeed,
            "MaximumSpeed": maxspeed,
            "StartLon": start_lon,
            "StartLat": start_lat,
            "EndLon": end_lon,
            "EndLat": end_lat,
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

