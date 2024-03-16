import requests
import pandas as pd
import datetime
import os
import json

class WeatherForecastAPI:
    def __init__(self):
        self.base_url = "https://api.data.gov.sg/v1"
        self.api_urls = {"2-hour-weather-forecast": "/environment/2-hour-weather-forecast"}

    def call(self, api_name, date_time=None, output_file="weatherforecast.csv"):
        """
        Fetches data from the specified Data.gov.sg API and saves it to a CSV file.

        """
        api_url = self.base_url + self.api_urls[api_name]
        params = {}
        if date_time:
            params['date_time'] = date_time
        response = requests.get(api_url, params=params)
        if response.status_code != 200:
            raise requests.exceptions.HTTPError(f"Did not get status 200 from response, got {response.status_code}")
        data = response.json()
        if 'items' in data and data['items']:
            forecasts = data['items'][0]['forecasts']
            current_timestamp = datetime.datetime.now().isoformat()
            df_data = [{
                'area': forecast['area'],
                'forecast': forecast['forecast'],
                'timestamp': current_timestamp
            } for forecast in forecasts]

            df = pd.DataFrame(df_data)
            df.columns = [col.lower() for col in df.columns]

            if os.path.exists(output_file):
                print(f"Appending to existing {output_file}")
                df.to_csv(output_file, mode='a', header=False, index=False)
            else:
                print(f"Creating new {output_file}")
                df.to_csv(output_file, index=False)
            print(f"Download and save/update completed for {output_file}")
        else:
            print("No data available for the specified datetime.")
