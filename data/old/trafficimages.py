import requests
import pandas as pd
import datetime
import urllib.request
import matplotlib.image as img
import matplotlib.pyplot as plt
from aws import AWS
from data_utils import upload_to_s3

class TrafficImages:
    """
    The module will download all the 90 images from LTA data mall into the current working dir.
    Call retrieve_image(camera_id) method to retrieve a specific image given a specific camera
    """
    def __init__(self, camera_id='all'):
        api_url = 'http://datamall2.mytransport.sg/ltaodataservice/Traffic-Imagesv2'
        headers = {'AccountKey': api_key}
        self.camera_id = str(camera_id)
        self.response = requests.get(api_url, headers=headers)
        self.image_data = self.download_all()
        self.camera_list = self.image_data['CameraID'].tolist()
        self.s3 = AWS().s3

    def download_local(self):
        tot_cam = len(self.response.json()["value"])
        timestamp = datetime.datetime.now()
        cameraid = []
        latitude = []
        longitude = []
        imagelink = []
        filename = []
        for i in range(0, tot_cam):
            cameraid.append(self.response.json()["value"][i]["CameraID"])
            latitude.append(self.response.json()["value"][i]["Latitude"])
            longitude.append(self.response.json()["value"][i]["Longitude"])
            imagelink.append(self.response.json()["value"][i]["ImageLink"])
            filename.append(self.response.json()["value"][i]["CameraID"] + '_' + timestamp + '.jpg')

            urllib.request.urlretrieve(self.response.json()["value"][i]["ImageLink"],
                                       self.response.json()["value"][i]["CameraID"] + '_' + timestamp + '.jpg')

        # Create a DataFrame with the extracted data
        data = pd.DataFrame({
            "cameraid": cameraid,
            "latitude": latitude,
            "Longitude": longitude,
            "imagelink": imagelink,
            "filename": filename,
        })
        if self.camera_id == 'all':
            print('Download all completed \n', data.head(5))
        return data

    def retrieve_image(self, camera_id):
        camera_id = str(camera_id)
        if camera_id in self.camera_list:
            print("Retrieving")
            filename = self.image_data.loc[self.image_data['CameraID'] == camera_id, 'Filename'].values[0]
            try:
                image = img.imread(filename)
                plt.imshow(image)
                plt.show()
                return image
            except FileNotFoundError:
                print(f"Image file not found for CameraID '{camera_id}'")
                return None
        else:
            print('Camera ID not valid')
            return None

    def download_s3(self):
        data = self.download_local(self)
        # Get a list of filenames from the DataFrame column
        filenames = data['filename'].tolist()
        # Iterate through each filename and upload using your function
        for filename in filenames:
            try:
                self.upload('dba5102', filename, filename)  # Call your upload function
                print(f"Uploaded: {filename}")
            except Exception as e:
                print(f"Error uploading {filename}: {e}")
        return