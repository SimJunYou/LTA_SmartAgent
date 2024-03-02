import requests
import pandas as pd
import datetime
import os
class FaultyTrafficLights:
    """
    The module will download alerts of traffic lights currently faulty or undergoing maintenance from LTA data mall into the current working dir.
    Call download_all method with an output file name to append the data
    """

    def __init__(self, api_key='DZ4mqxgDSyqDNLVqkIMCog=='):
        api_url = 'http://datamall2.mytransport.sg/ltaodataservice/FaultyTrafficLights'
        headers = {'AccountKey': api_key}
        self.response = requests.get(api_url, headers=headers)

    def download_all(self, output_file='faulty_traffic_lights.csv'):
        total = len(self.response.json()["value"])
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        if total == 0:
            print('There is no fault traffic light at', timestamp)
            return None

        alarm_id = []
        node_id = []
        alarm_type = []
        start_date = []
        end_date = []
        message = []

        for i in range(0, total):
            alarm_id.append(self.response.json()["value"][i]["AlarmID"])
            node_id.append(self.response.json()["value"][i]["NodeID"])
            alarm_type.append(self.response.json()["value"][i]["Type"])
            start_date.append(self.response.json()["value"][i]["StartDate"])
            end_date.append(self.response.json()["value"][i]["EndDate"])
            message.append(self.response.json()["value"][i]["Message"])

        # Create a DataFrame with the extracted data
        data = pd.DataFrame({
            "AlarmID": alarm_id,
            "NodeID": node_id,
            "Type": alarm_type,
            "StartDate": start_date,
            "EndDate": end_date,
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
