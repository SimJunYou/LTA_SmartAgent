import requests
import pandas as pd
import datetime
import os
from aws import AWS
from data.data_utils import upload_to_s3

class AirTemperatureData:
    """
    The module will download air temperature readings from the specified API into the current working dir.
    Call download_local method with an output file name to append the data.
    """

    def __init__(self):
        self.api_url = "https://api.data.gov.sg/v1/environment/air-temperature"
        self.s3 = AWS().s3

    def fetch_data(self, date_time):
        params = {'date_time': date_time}
        response = requests.get(self.api_url, params=params)
        return response.json() if response.status_code == 200 else None

    def download_local(self, date_time, output_file="airtemp.csv"):
        data = self.fetch_data(date_time)
        if data and 'items' in data and data['items']:
            station_info = {station['id']: {'name': station['name'],
                                            'latitude': station['location']['latitude'],
                                            'longitude': station['location']['longitude']}
                            for station in data['metadata']['stations']}

            current_timestamp = datetime.datetime.now()
            df_data = [{
                'stationid': reading['station_id'],
                'temperature': reading['value'],
                'stationname': station_info[reading['station_id']]['name'],
                'latitude': station_info[reading['station_id']]['latitude'],
                'longitude': station_info[reading['station_id']]['longitude'],
                'timestamp': current_timestamp
            } for reading in data['items'][0]['readings']]

            df = pd.DataFrame(df_data)
            print('Download all completed, updating to', output_file)
            if os.path.exists(output_file):
                print("Appending to existing", output_file)
                df.to_csv(output_file, mode='a', header=False, index=False)
            else:
                print("Creating new", output_file)
                df.to_csv(output_file, index=False)
        else:
            print("No air temperature data available for the specified datetime.")

    def download_s3(self, output_file="airtemp.csv"):
        data = self.download_local(output_file)
        upload_to_s3('airtemp', data)
        return data
