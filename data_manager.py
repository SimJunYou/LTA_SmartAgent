import os
import dotenv
import datetime

from sqlalchemy import create_engine, text

from aws import AWS
from utils.all_tables_query import CREATE_TABLES_QUERY, DROP_TABLES_QUERY


config = dotenv.dotenv_values(".env")


class DataManager:
    """
    The DataManager class interacts directly with the database and API calling interfaces
    to funnel data directly from APIs to the database. All logic related to database interaction
    should be placed in this class. Interactions between API data and AWS S3 should also be
    included in this class.
    """

    def __init__(self):
        if config["IS_TEST_ENV"]:
            self.database = Database()
        else:
            self.aws = AWS()
            instance_id = aws.rds.listInstance()
            endpoint, port = aws.rds.readInstance(instance_id)
            self.database = Database(endpoint=endpoint, port=port)

        # Expose connection string for initialization of Langchain SQL toolkit
        self.connection_str = self.database.connection_str

        self.datamall = DatamallInterface(config["DATAMALL_API_KEY"])
        self.datamall_apis = [
            "carpark",
            "erprates",
            "esttraveltimes",
            "faultytrafficlights",
            "roadopenings",
            "roadworks",
            "trafficimages",
            "trafficincidents",
            "trafficspeedbands",
            "vms",
        ]
        self.weather_apis = [
            "",
        ]

    def full_db_refresh(self):
        self.database.drop_all_tables()
        self.database.create_all_tables()
        for api_name in self.datamall_apis:
            self.update_table(api_name)

    def update_table(self, api_name):
        if api_name in self.datamall_apis:
            data = self.datamall.call(api_name)
        elif api_name in self.weather_apis:
            raise NotImplementedError("No weather APIs connected yet!")
        else:
            raise KeyError(f"Datamall API {api_name} is not available!")

        self.database.update_table_from_df(data, api_name)


class Database:
    """
    Simple interface for an SQLAlchemy connection. Arbitrary queries can be run using
    run_query for testing purposes, but when used in production, additional methods should
    be written to run those queries in a rigid and safe manner.
    """

    def __init__(self, endpoint="localhost", port="5432"):
        if endpoint is None or port is None:
            raise Exception("Endpoint or port cannot be empty!")

        print(f"Connecting to database instance {endpoint}:{port}")

        db_user, db_pw, db_name = (
            config["DB_USER"],
            config["db_password"],
            config["db_name"],
        )
        self.connection_str = (
            f"postgresql://{db_user}:{db_pw}@{endpoint}:{port}/{db_name}"
        )
        self.engine = create_engine(self.connection_str)

    def create_all_tables(self):
        return self.run_query(CREATE_TABLES_QUERY, expect_results=False)

    def drop_all_tables(self):
        return self.run_query(DROP_TABLES_QUERY, expect_results=False)

    def update_table_from_df(self, df, table_name):
        try:
            with self.engine.connect() as conn:
                df.to_sql(table_name, conn, if_exists="replace", index=False)
                conn.commit()
        except Exception as err:
            print(f"Error updating table from DataFrame: {err}")

    def run_query(self, query, expect_results=True):
        print(f"Running query: {query[:100]}")
        try:
            # Connect to the DB
            with self.engine.connect() as conn:
                res = conn.execute(text(query))
                conn.commit()
            # automatically close connection
        except Exception as err:
            print(f"Error running query: {err}")
            return False
        if expect_results:
            results = res.fetchall()
            return results

    # def update_tables_from_s3(self, s3_instance):
    #     # Pass in S3 instance when using this
    #     print(f"Updating the following tables: {self.table_names}")
    #     try:
    #         with self.engine.connect() as conn:
    #             for table_name in self.table_names:
    #                 print(f"Updating {table_name}...")
    #                 df = s3_instance.readObject("dba5102", f"{table_name}.csv")
    #                 df.to_sql(table_name, conn, if_exists="replace", index=False)
    #             conn.commit()
    #             # automatically close connection

    #     except Exception as err:
    #         print(f"Error updating table from S3: {err}")


class DatamallInterface:
    """
    Simple interface for the LTA Datamall API. Using a mapping of table names to
    corresponding API URLs, we only need the table name to call the appropriate
    API. To add new Datamall APIs, change the code in this interface.
    """

    def __init__(self, api_key):
        self.headers = {"AccountKey": api_key}
        self.base_url = "http://datamall2.mytransport.sg/ltaodataservice/"
        self.api_urls = {
            "carpark": "CarParkAvailabilityv2",
            "erprates": "ERPRates",
            "esttraveltimes": "EstTravelTimes",
            "faultytrafficlights": "FaultyTrafficLights",
            "roadopenings": "RoadOpenings",
            "roadworks": "RoadWorks",
            "trafficincidents": "TrafficIncidents",
            "trafficspeedbands": "v3/TrafficSpeedBands",
            "trafficimages": "Traffic-Imagesv2",
            "vms": "VMS",
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
        response = requests.get(api_url, headers=self.headers)

        # check success of API call to avoid bad data
        if response.status_code != 200:
            raise requests.exceptions.HTTPError("Did not get status 200 from response")

        # our tables are in the same schema as the response data
        # directly convert to a dataframe using pd.DataFrame.from_records
        res_val = json.loads(response.text)["value"]
        data = pd.DataFrame.from_records(res_val)

        # make columns lowercase to match schema in our database
        data.columns = [col.lower() for col in data.columns]
        data["timestamp"] = datetime.datetime.now()
        return data

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

    # def download_s3(self, output_file="carpark.csv"):
    #     data = self.download_local(output_file)
    #     upload_to_s3("carpark", data)
    #     return data
