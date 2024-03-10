import requests
import psycopg2
import pandas as pd
import datetime
import os
import dotenv

dotenv.load_dotenv()

DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_HOST = "localhost"
DB_PORT = "5432"
LTA_DATAMALL_API_KEY = os.environ.get("DATAMALL_API_KEY")

class LocalDatabase:
    def __init__(self):
        self.connection_string = f"dbname='{DB_NAME}' user='{DB_USER}' password='{DB_PASSWORD}' host='{DB_HOST}' port='{DB_PORT}'"
        self.conn = psycopg2.connect(self.connection_string)

    def create_table(self, table_name, table_definition):
        with self.conn.cursor() as cursor:
            cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({table_definition});")
            self.conn.commit()
            print(f"Table '{table_name}' created successfully.")

    def insert_data(self, table_name, data_frame):
        with self.conn.cursor() as cursor:
            for index, row in data_frame.iterrows():
                columns = ', '.join(row.index)
                # Format the timestamp value
                timestamp_str = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f')
                # Remove 'timestamp' column from columns and row.values
                columns = ', '.join([col for col in row.index if col != 'timestamp'])
                values = ', '.join([f"'{value}'" if isinstance(value, str) else str(value) for col, value in row.items() if col != 'timestamp'])
                # Add formatted timestamp to the values
                values = f"{values}, '{timestamp_str}'"
                cursor.execute(f"INSERT INTO {table_name} ({columns}, timestamp) VALUES ({values});")
            self.conn.commit()
            print(f"Data inserted into table '{table_name}' successfully.")

    def query_data(self, query):
        with self.conn.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            return results

    def close(self):
        self.conn.close()
        print("Database connection closed.")

class CarParkData:
    def __init__(self, api_key):
        self.api_url = "http://datamall2.mytransport.sg/ltaodataservice/CarParkAvailabilityv2"
        self.headers = {"AccountKey": api_key}

    def download_data(self):
        response = requests.get(self.api_url, headers=self.headers)
        data = response.json()["value"]
        df = pd.DataFrame(data)
        df["timestamp"] = datetime.datetime.now()
        return df

# Example usage
if __name__ == "__main__":
    db = LocalDatabase()

    # Create a table for car park data
    db.create_table("carpark", """
        carparkid TEXT,
        area TEXT,
        development TEXT,
        location TEXT,
        availablelots INTEGER,
        lottype TEXT,
        agency TEXT,
        timestamp TIMESTAMP
    """)

    # Download car park data from LTA DataMall
    carpark_data = CarParkData(LTA_DATAMALL_API_KEY)
    data = carpark_data.download_data()

    # Insert the downloaded data into the local database
    db.insert_data("carpark", data)

    # Query and print some data from the table
    results = db.query_data("SELECT * FROM carpark LIMIT 5;")
    for row in results:
        print(row)

    # Close the database connection
    db.close()
