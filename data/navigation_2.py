import datetime
from urllib.parse import urlencode
import requests
from bs4 import BeautifulSoup


class Navigation_2:
    """
    The module will provide the steps to go from origin point to end point
    origin and end point must be a text string consisting of
    a) 'start_lat,start_lon'
    b) address such as '853 Hougang Central'
    c) Postal code

    The module can process a list of things to avoid (avoid = ['pizza', 'tolls', 'police'])

    The module will provide response with multiple transport modes such as driving, walking, bicycling, transit (public transport)

    """

    def __init__(self, origin, destination, google_api_key, mode='driving', alternatives=True, avoid=[]):
        self.alternatives = alternatives
        avoid_list_const = ['tolls', 'highways', 'ferries', 'indoor']
        avoid_list = []

        for thing_to_avoid in avoid:
            if thing_to_avoid in avoid_list_const:
                avoid_list.append(thing_to_avoid)

        self.avoid_str = '|'.join(avoid_list)

        timestamp = datetime.datetime.now()
        timestamp_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        self.output_file = f'navigation-{timestamp_str}.txt'
        self.origin = origin
        self.destination = destination
        self.validate_address(google_api_key)

    def validate_address(self, google_api_key):
        verified_origin = self.text_query(self.origin, google_api_key)
        verified_destination = self.text_query(self.destination, google_api_key)

        if len(verified_origin) > 1:
            print('There are more than 1 place matching your original location')
            print(location for location in verified_origin)

        else:
            self.origin = verified_origin[0]

        if len(verified_destination) > 1:
            print('There are more than 1 place matching your destination location')
            print(location for location in verified_destination)
        else:
            self.destination = verified_destination[0]

    def text_query(self, query, google_api_key):
        url = "https://places.googleapis.com/v1/places:searchText"
        params = {"textQuery": query}
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": google_api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress"  # ,places.priceLevel"
        }

        response = requests.post(url, json=params, headers=headers)

        return [place['formattedAddress'] for place in response.json()['places']]

    def query(self, params):
        query_string = urlencode(params)

        # Construct the complete URL
        base_url = "https://maps.googleapis.com/maps/api/directions/json?"
        url = base_url + query_string
        return requests.request('Get', url)

    def write_to_file(self, response):
        clean_steps = []
        total_distance = []
        total_duration = []

        options = len(response.json()["routes"])
        if options > 0:
            print(f'There are {options} options to go there:')

            for k in range(0, options):
                steps = []
                for i in range(0, len(response.json()['routes'][k]['legs'][0]['steps'])):
                    steps.append(
                        response.json()['routes'][k]['legs'][0]['steps'][i]['html_instructions']
                    )
                clean_steps.append([BeautifulSoup(step, "html.parser").get_text().strip() for step in steps])
                total_distance.append(response.json()['routes'][k]['legs'][0]['distance']['text'])
                total_duration.append(response.json()['routes'][k]['legs'][0]['duration']['text'])

            with open(self.output_file, "a") as file:
                for k in range(0, options):
                    newline = f'Option {k} takes {total_duration[k]} and is {total_distance[k]} long!'
                    file.writelines([newline, '\n'])
                    for line in clean_steps[k]:
                        file.writelines(line)
                    file.writelines(['\n', '\n'])

            print('Navigation steps written successfully to', self.output_file)

        else:
            print('Exact address not found, please try again.')

        return

    def driving(self, google_api_key):
        mode = 'driving'
        params_driving = {
            'origin': self.origin,
            'destination': self.destination,
            'alternatives': self.alternatives,
            'mode': mode,
            'avoid': self.avoid_str,
            'key': google_api_key
        }
        self.write_to_file(self.query(params_driving))
        return

    def publictransport(self, google_api_key):
        mode = 'transit'
        params_public = {
            'origin': self.origin,
            'destination': self.destination,
            'alternatives': self.alternatives,
            'mode': mode,
            'avoid': self.avoid_str,
            'key': google_api_key
        }

        self.write_to_file(self.query(params_public))
        return

# Here is how to test this function
#origin = 'NUS LT15'
#destination = 'Fairmont hotel'   # I select this one because by default the API will not recognize it
#avoid = ['pizza', 'tolls', 'police']
# test = Navigation_2(
#     origin,
#     destination,
#     alternatives='true',
#     avoid=avoid,
#     google_api_key=google_api_key
# )

# Check if the address has been converted automatically to a valid one
# test.origin
# test.destination
# Create navigation routes with driving mode
# test.driving(google_api_key)
# Create navigation routes with public transportation mode
# test.publictransport(google_api_key)
# The output is written to a text file

# For free text search, try this
#test.text_query('parking near'+test.destination, google_api_key)