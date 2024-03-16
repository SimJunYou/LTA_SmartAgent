import datetime
import os
from urllib.parse import urlencode
import requests
from bs4 import BeautifulSoup


class Navigation_2:
    """
    The module will provide the steps to go from origin point to end point
    origin and end point must be a text string consisting of
    a) 'start_lat,start_lon'
    b) address such as '853 Hougang Central'

    The module can process a list of things to avoid (avoid = ['pizza', 'tolls', 'police'])

    The module support driving, walking, bicycling, transit (public transport)

    """

    def __init__(self, origin, destination, google_api_key, mode='driving', alternatives=None, avoid=[]):
        avoid_list_const = ['tolls', 'highways', 'ferries', 'indoor']
        avoid_list = []
        for thing_to_avoid in avoid:
            if thing_to_avoid in avoid_list_const:
                avoid_list.append(thing_to_avoid)
        avoid_str = '|'.join(avoid_list)

        mode_list_const = ['driving', 'walking', 'bicycling', 'transit']
        if mode not in mode_list_const:
            mode = 'driving'

        self.origin = origin
        self.destination = destination
        self.avoid_str = avoid_str

        params = {
            'origin': self.origin,
            'destination': self.destination,
            'alternatives': alternatives,
            'mode': mode,
            'avoid': self.avoid_str,
            'key': google_api_key
        }

        query_string = urlencode(params)
        print(query_string)

        # Construct the complete URL
        base_url = "https://maps.googleapis.com/maps/api/directions/json?"
        url = base_url + query_string
        self.response = requests.request('Get', url)

    def download_all(self, output_file='navigation.txt'):
        timestamp = datetime.datetime.now()
        timestamp_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        clean_steps = []
        total_distance = []
        total_duration = []

        options = len(self.response.json()["routes"])
        if options > 0:
            print(f'There are {options} options to go there:')

            for k in range(0, options):
                steps = []
                for i in range(0, len(self.response.json()['routes'][k]['legs'][0]['steps'])):
                    steps.append(
                        self.response.json()['routes'][k]['legs'][0]['steps'][i]['html_instructions']
                    )
                clean_steps.append([BeautifulSoup(step, "html.parser").get_text().strip() for step in steps])
                total_distance.append(self.response.json()['routes'][k]['legs'][0]['distance']['text'])
                total_duration.append(self.response.json()['routes'][k]['legs'][0]['duration']['text'])

            if os.path.exists(output_file):
                # File exists, save to a new file with timestamp
                output_file = f'{output_file.split(".txt")[0]}{timestamp_str}.txt'
                print("Same filename already exists, saving to ", output_file)

            with open(output_file, "w") as file:
                for k in range(0, options):
                    newline = f'Option {k} takes {total_duration[k]} and is {total_distance[k]} long!'
                    file.writelines([newline, '\n'])
                    for line in clean_steps[k]:
                        file.writelines(line)
                    file.writelines(['\n', '\n'])

            print('Navigation steps written successfully to', output_file)

        else:
            print('Exact address not found, please try again.')

        return