import requests
import pandas as pd
import datetime
import os
from aws import AWS
from data_utils import upload_to_s3

class ERP_Rates:
    """
    The module will download ERP rates from LTA data mall into the current working dir.
    Call download_all method with an output file name to append the data
    """
    def __init__(self, api_key):
        api_url = 'http://datamall2.mytransport.sg/ltaodataservice/ERPRates'
        headers = {'AccountKey': api_key}
        self.response = requests.get(api_url, headers=headers)
        self.s3 = AWS().s3

    def download_local(self, output_file='erprates.csv'):
        total = len(self.response.json()["value"])
        vehicletype = []
        daytype = []
        starttime = []
        endtime = []
        zoneid = []
        chargeamount = []
        effectivedate = []
        timestamp = datetime.datetime.now()

        for i in range(0, total):
            vehicletype.append(self.response.json()["value"][i]["VehicleType"])
            daytype.append(self.response.json()["value"][i]["DayType"])
            starttime.append(self.response.json()["value"][i]["StartTime"])
            endtime.append(self.response.json()["value"][i]["EndTime"])
            zoneid.append(self.response.json()["value"][i]["ZoneID"])
            chargeamount.append(self.response.json()["value"][i]["ChargeAmount"])
            effectivedate.append(self.response.json()["value"][i]["EffectiveDate"])

        # Create a DataFrame with the extracted data
        data = pd.DataFrame({
            "vehicletype": vehicletype,
            "daytype": daytype,
            "starttime": starttime,
            "endtime": endtime,
            "zoneid": zoneid,
            "chargeamount": chargeamount,
            "effectivedate": effectivedate,
        })
        data['timestamp'] = timestamp
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

    def download_s3(self, output_file="erprates.csv"):
        data = self.download_local(self, output_file)
        upload_to_s3('erprates', data)
        return data