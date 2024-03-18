import os
import json
import datetime
import requests

import dotenv
import pandas as pd
from sqlalchemy import create_engine, text

from aws import AWS
from data.WeatherInterface import WeatherInterface
from data.DatamallInterface import DatamallInterface
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
        self.weather = WeatherInterface()
        self.weather_apis = [
            "airtemp",
            "psi",
            "rainfall",
            "weatherforecast",
        ]

    def full_db_refresh(self):
        self.database.drop_all_tables()
        self.database.create_all_tables()
        for api_name in self.datamall_apis:
            self.update_table(api_name)
        for api_name in self.weather_apis:
            self.update_table(api_name)

    def query(self, query):
        return pd.DataFrame(self.database.run_query(query))

    def update_table(self, api_name):
        if api_name in self.datamall_apis:
            data = self.datamall.call(api_name)
        elif api_name in self.weather_apis:
            data = self.weather.call(api_name)
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
            config["DB_PASSWORD"],
            config["DB_NAME"],
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


# Create a DataManager singleton - this should be used from everywhere using the helper function below
DM_SINGLETON = DataManager()


def data_manager():
    return DM_SINGLETON
