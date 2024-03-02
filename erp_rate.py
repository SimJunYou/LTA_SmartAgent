import requests
import pandas as pd
import datetime
import os
class ERP_Rates:
    """
    The module will download ERP rates from LTA data mall into the current working dir.
    Call download_all method with an output file name to append the data
    """
    def __init__(self, api_key='DZ4mqxgDSyqDNLVqkIMCog=='):
        api_url = 'http://datamall2.mytransport.sg/ltaodataservice/ERPRates'
        headers = {'AccountKey': api_key}
        self.response = requests.get(api_url, headers=headers)

    def download_all(self, output_file='erp_rates.csv'):
        total = len(self.response.json()["value"])
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")

        vehicle_type = []
        day_type = []
        start_time = []
        end_time = []
        zone_id = []
        charge_amount = []
        effective_date = []

        for i in range(0, total):
            vehicle_type.append(self.response.json()["value"][i]["VehicleType"])
            day_type.append(self.response.json()["value"][i]["DayType"])
            start_time.append(self.response.json()["value"][i]["StartTime"])
            end_time.append(self.response.json()["value"][i]["EndTime"])
            zone_id.append(self.response.json()["value"][i]["ZoneID"])
            charge_amount.append(self.response.json()["value"][i]["ChargeAmount"])
            effective_date.append(self.response.json()["value"][i]["EffectiveDate"])

        # Create a DataFrame with the extracted data
        data = pd.DataFrame({
            "VehicleType": vehicle_type,
            "DayType": day_type,
            "StartTime": start_time,
            "EndTime": end_time,
            "ZoneID": zone_id,
            "ChargeAmount": charge_amount,
            "EffectiveDate": effective_date,
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