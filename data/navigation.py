import requests
import os
from bs4 import BeautifulSoup
from urllib.parse import urlencode


# import json

class Navigation:
    """
    The module will provide the steps to go from starting point to destination

    """

    def __init__(self, start_lat, start_lon, end_lat, end_lon, google_api_key):

        self.origin = start_lat + ',' + start_lon
        self.destination = end_lat + ',' + end_lon
        params = {
            'origin': self.origin,
            'destination': self.destination,
            'key': google_api_key
        }

        query_string = urlencode(params)

        # Construct the complete URL
        base_url = "https://maps.googleapis.com/maps/api/directions/json?"
        url = base_url + query_string
        self.response = requests.request('Get', url)
        print('Total distance', self.response.json()['routes'][0]['legs'][0]['distance']['text'])
        print('Total duration', self.response.json()['routes'][0]['legs'][0]['duration']['text'])

    def download_all(self, output_file='navigation.txt'):
        steps = []
        for i in range(0, len(self.response.json()['routes'][0]['legs'][0]['steps'])):
            steps.append(
                self.response.json()['routes'][0]['legs'][0]['steps'][i]['html_instructions']
            )

        clean_steps = [BeautifulSoup(step, "html.parser").get_text().strip() for step in steps]

        if os.path.exists(output_file):
            # File exists, append to it
            print("Same filename already exists, not saving to file!", output_file)

        else:
            # File does not exist, create a new one
            with open(output_file, "w") as file:
                for line in clean_steps:
                    file.writelines(line + '\n')
            print('Navigation steps written successfully to', output_file)

        return clean_steps
