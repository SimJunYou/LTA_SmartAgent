import requests
import pandas as pd
import datetime
import os

class RoadOpenings:
    """
    The module will download road openings from LTA data mall into the current working dir.
    Call download_all method with an output file name to append the data
    """
    def __init__(self, api_key='DZ4mqxgDSyqDNLVqkIMCog=='):
        api_url = 'http://datamall2.mytransport.sg/ltaodataservice/RoadOpenings'
        headers = {'AccountKey': api_key}
        self.response = requests.get(api_url, headers=headers)

    def download_all(self, output_file='data.csv'):
        total = len(self.response.json()["value"])
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        if total == 0:
            print('No road opening at the moment')
            return None

        event_id = []
        start_date = []
        end_date = []
        svc_dept = []
        road_name = []
        other = []

        for i in range(0, total):
            event_id.append(self.response.json()["value"][i]["EventID"])
            start_date.append(self.response.json()["value"][i]["StartDate"])
            end_date.append(self.response.json()["value"][i]["EndDate"])
            svc_dept.append(self.response.json()["value"][i]["SvcDept"])
            road_name.append(self.response.json()["value"][i]["RoadName"])
            other.append(self.response.json()["value"][i]["Other"])

        # Create a DataFrame with the extracted data
        data = pd.DataFrame({
            "EventID": event_id,
            "StartDate": start_date,
            "EndDate": end_date,
            "SvcDept": svc_dept,
            "RoadName": road_name,
            "Other": other,
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
