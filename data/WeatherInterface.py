import requests
import json
import datetime

import pandas as pd


class WeatherInterface:
    """
    Simple interface for the LTA Datamall API. Using a mapping of table names to
    corresponding API URLs, we only need the table name to call the appropriate
    API. To add new Datamall APIs, change the code in this interface.
    """

    def __init__(self):
        self.base_url = "https://api.data.gov.sg/v1/"
        self.api_urls = {
            "airtemp": "environment/air-temperature",
            "psi": "environment/psi",
            "rainfall": "environment/rainfall",
            "weatherforecast": "environment/2-hour-weather-forecast",
        }  # the keys here are the corresponding table names in the database

    def call(self, api_name):
        """
        Saves data from a Datamall API call to a Pandas DataFrame and returns it.

        :param api_name: the name of the API to be called
        :param output_file: the name of the CSV file to save the data to
        :returns: dataframe of API response data
        :raises HTTPError: if API call fails
        """
        api_url = self.base_url + self.api_urls[api_name]
        response = requests.get(api_url)

        # check success of API call to avoid bad data
        if response.status_code != 200:
            raise requests.exceptions.HTTPError("Did not get status 200 from response")

        # our tables are in the same schema as the response data
        # directly convert to a dataframe using pd.DataFrame.from_records
        res_val = json.loads(response.text)
        if api_name == "airtemp":
            data = self.unpack_air_temp(res_val)
        elif api_name == "psi":
            data = self.unpack_psi(res_val)
        elif api_name == "rainfall":
            data = self.unpack_rainfall(res_val)
        elif api_name == "weatherforecast":
            data = self.unpack_forecast(res_val)

        # make columns lowercase to match schema in our database
        data.columns = [col.lower() for col in data.columns]
        data["timestamp"] = datetime.datetime.now()
        return data

    def unpack_air_temp(self, data):
        station_info = {
            station["id"]: {
                "name": station["name"],
                "latitude": station["location"]["latitude"],
                "longitude": station["location"]["longitude"],
            }
            for station in data["metadata"]["stations"]
        }

        current_timestamp = datetime.datetime.now()
        df_data = [
            {
                "stationid": reading["station_id"],
                "temperature": reading["value"],
                "stationname": station_info[reading["station_id"]]["name"],
                "latitude": station_info[reading["station_id"]]["latitude"],
                "longitude": station_info[reading["station_id"]]["longitude"],
                "timestamp": current_timestamp,
            }
            for reading in data["items"][0]["readings"]
        ]
        return pd.DataFrame(df_data)

    def unpack_rainfall(self, data):
        station_info = {
            station["id"]: {
                "name": station["name"],
                "latitude": station["location"]["latitude"],
                "longitude": station["location"]["longitude"],
            }
            for station in data["metadata"]["stations"]
        }

        current_timestamp = datetime.datetime.now()
        df_data = [
            {
                "stationid": reading["station_id"],
                "rainfall": reading["value"],
                "stationname": station_info[reading["station_id"]]["name"],
                "latitude": station_info[reading["station_id"]]["latitude"],
                "longitude": station_info[reading["station_id"]]["longitude"],
                "timestamp": current_timestamp,
            }
            for reading in data["items"][0]["readings"]
            if station_info[reading["station_id"]]["name"] != reading["station_id"]
        ]
        return pd.DataFrame(df_data)

    def unpack_forecast(self, data):
        forecasts = data["items"][0]["forecasts"]
        current_timestamp = datetime.datetime.now().isoformat()
        df_data = [
            {
                "area": forecast["area"],
                "forecast": forecast["forecast"],
                "timestamp": current_timestamp,
            }
            for forecast in forecasts
        ]
        return pd.DataFrame(df_data)

    def unpack_psi(self, data):
        region_to_areas = {
            "north": [
                "Admirality",
                "Kranji",
                "Woodlands",
                "Sembawang",
                "Yishun",
                "Yio Chu Kang",
                "Seletar",
                "Punggol",
                "Sengkang",
            ],
            "south": [
                "Holland",
                "Queenstown",
                "Bukit Merah",
                "Telok Blangah",
                "Pasir Panjang",
                "Sentosa",
                "Bukit Timah",
                "Newton",
                "Orchard",
                "City",
                "Marina South",
            ],
            "east": [
                "Serangoon",
                "Hougang",
                "Tampines",
                "Pasir Ris",
                "Loyang",
                "Simei",
                "Kallang",
                "Katong",
                "East Coast",
                "Macpherson",
                "Bedok",
                "Pulau Ubin",
                "Pulau Tekong",
            ],
            "west": [
                "Lim Chu Kang",
                "Choa Chu Kang",
                "Bukit Panjang",
                "Tuas",
                "Jurong East",
                "Jurong West",
                "Jurong Industrial Estate",
                "Bukit Batok",
                "Hillview",
                "West Coast",
                "Clementi",
            ],
            "central": [
                "Thomson",
                "Marymount",
                "Sin Ming",
                "Ang Mo Kio",
                "Bishan",
                "Serangoon Gardens",
                "MacRitchie",
                "Toa Payoh",
            ],
        }
        psi_bands = [
            (0, 50, "Good"),
            (51, 100, "Moderate"),
            (101, 200, "Unhealthy"),
            (201, 300, "Very Unhealthy"),
            (301, float("inf"), "Hazardous"),
        ]

        def get_psi_band(psi_value):
            for lower_bound, upper_bound, descriptor in psi_bands:
                if lower_bound <= psi_value <= upper_bound:
                    return descriptor
            return "Unknown"

        current_timestamp = datetime.datetime.now()
        df_data = []
        for item in data["items"]:
            psi_readings = item["readings"]["psi_twenty_four_hourly"]
            for region in data["region_metadata"]:
                region_name = region["name"]
                areas = ", ".join(region_to_areas.get(region_name, []))
                psi_value = psi_readings.get(region_name, "N/A")
                psi_band = get_psi_band(psi_value) if psi_value != "N/A" else "N/A"
                df_data.append(
                    {
                        "region": region_name,
                        "area": areas,
                        "psi": psi_value,
                        "psi_band": psi_band,
                        "timestamp": current_timestamp,
                    }
                )
        return pd.DataFrame(df_data)

    def download_local(self, api_name, output_file):
        """
        Saves data from a Datamall API call to a CSV file.

        :param api_name: the name of the API to be called
        :param output_file: the name of the CSV file to save the data to
        """
        data = self.call(api_name)
        print("Download completed, updating to", output_file)
        # Check if the file exists
        if os.path.exists(output_file):
            # File exists, append to it
            print("Appending to existing", output_file)
            data.to_csv(output_file, mode="a", header=False, index=False)
        else:
            # File does not exist, create a new one
            print("Creating new", output_file)
            data.to_csv(output_file, index=False)


test = WeatherInterface()
print(test.call("airtemp").head())
print(test.call("rainfall").head())
print(test.call("psi").head())
print(test.call("weatherforecast").head())
