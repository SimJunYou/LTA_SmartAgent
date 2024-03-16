import requests
import pandas as pd
import datetime
import os
from aws import AWS
from data.data_utils import upload_to_s3

class PSIData:
    """
    The module will download the latest PSI readings from the specified API into the current working dir.
    Call download_local method with an output file name to append the data.
    """

    def __init__(self):
        self.api_url = "https://api.data.gov.sg/v1/environment/psi"
        self.s3 = AWS().s3
        self.region_to_areas = {
            "north": ["Admirality", "Kranji", "Woodlands", "Sembawang", "Yishun", "Yio Chu Kang", "Seletar", "Punggol", "Sengkang"],
            "south": ["Holland", "Queenstown", "Bukit Merah", "Telok Blangah", "Pasir Panjang", "Sentosa", "Bukit Timah", "Newton", "Orchard", "City", "Marina South"],
            "east": ["Serangoon", "Hougang", "Tampines", "Pasir Ris", "Loyang", "Simei", "Kallang", "Katong", "East Coast", "Macpherson", "Bedok", "Pulau Ubin", "Pulau Tekong"],
            "west": ["Lim Chu Kang", "Choa Chu Kang", "Bukit Panjang", "Tuas", "Jurong East", "Jurong West", "Jurong Industrial Estate", "Bukit Batok", "Hillview", "West Coast", "Clementi"],
            "central": ["Thomson", "Marymount", "Sin Ming", "Ang Mo Kio", "Bishan", "Serangoon Gardens", "MacRitchie", "Toa Payoh"],
        }
        self.psi_bands = [
            (0, 50, 'Good'),
            (51, 100, 'Moderate'),
            (101, 200, 'Unhealthy'),
            (201, 300, 'Very Unhealthy'),
            (301, float('inf'), 'Hazardous'),
        ]
        
    def fetch_data(self, date_time):
        params = {'date_time': date_time}
        response = requests.get(self.api_url, params=params)
        return response.json() if response.status_code == 200 else None

    def get_psi_band(self, psi_value):
        for lower_bound, upper_bound, descriptor in self.psi_bands:
            if lower_bound <= psi_value <= upper_bound:
                return descriptor
        return "Unknown"
    
    def download_local(self, date_time, output_file="psi.csv"):
        data = self.fetch_data(date_time)
        if data and 'items' in data and data['items']:
            current_timestamp = datetime.datetime.now()
            df_data = []
            for item in data['items']:
                psi_readings = item['readings']['psi_twenty_four_hourly']
                for region in data['region_metadata']:
                    region_name = region['name']
                    areas = ", ".join(self.region_to_areas.get(region_name, []))
                    psi_value = psi_readings.get(region_name, 'N/A')
                    psi_band = self.get_psi_band(psi_value) if psi_value != 'N/A' else 'N/A'
                    df_data.append({
                        'region': region_name,
                        'area': areas,
                        'psi': psi_value,
                        'psi_band': psi_band,
                        'timestamp': current_timestamp
                    })

            df = pd.DataFrame(df_data)
            print('Download all completed, updating to', output_file)
            if os.path.exists(output_file):
                print("Appending to existing", output_file)
                df.to_csv(output_file, mode='a', header=False, index=False)
            else:
                print("Creating new", output_file)
                df.to_csv(output_file, index=False)
        else:
            print("No PSI data available for the specified datetime.")

    def download_s3(self, output_file="psi.csv"):
        data = self.download_local(output_file)
        upload_to_s3('psi', data)
        return data
