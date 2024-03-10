import os
import dotenv
from sqlalchemy import create_engine, text

from utils.all_tables_query import CREATE_TABLES_QUERY, DROP_TABLES_QUERY

dotenv.load_dotenv()

DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")


class Database:
    def __init__(self, endpoint="localhost", port="5432"):
        if endpoint is None or port is None:
            raise Exception("Endpoint or port cannot be empty!")

        print(f"Connecting to database instance {endpoint}:{port}")

        self.connection_str = (
            f"postgresql://{DB_USER}:{DB_PASSWORD}@{endpoint}:{port}/{DB_NAME}"
        )
        self.engine = create_engine(self.connection_str)
        self.table_names = ["carpark"]
        # self.table_names = [
        #     "carpark",
        #     "erprates",
        #     "esttraveltimes",
        #     "faultytrafficlights",
        #     "roadopenings",
        #     "roadworks",
        #     "trafficimages",
        #     "trafficincidents",
        #     "trafficspeedbands",
        #     "vms",
        # ]

    def runQuery(self, query):
        print(f"Running query: {query[:100]}")
        try:
            # Connect to the DB
            with self.engine.connect() as conn:
                res = conn.execute(text(query))
                conn.commit()
                results = res.fetchall()
            # automatically close connection
        except Exception as err:
            print(f"Error running query: {err}")
            return False
        return results

    def createAllTables(self):
        return self.runQuery(CREATE_TABLES_QUERY)

    def dropAllTables(self):
        return self.runQuery(DROP_TABLES_QUERY)

    def updateTablesFromS3(self, s3_instance):
        # Pass in S3 instance when using this
        print(f"Updating the following tables: {self.table_names}")
        try:
            with self.engine.connect() as conn:
                for table_name in self.table_names:
                    print(f"Updating {table_name}...")
                    df = s3_instance.readObject("dba5102", f"{table_name}.csv")
                    df.to_sql(table_name, conn, if_exists="replace", index=False)
                conn.commit()
                # automatically close connection

        except Exception as err:
            print(f"Error updating table from S3: {err}")


# def main():
#     from aws import AWS

#     aws = AWS()
#     # instance_id = aws.rds.listInstance()[0]
#     # endpoint, port = aws.rds.readInstance(instance_id)
#     # print(endpoint, port)
#     db = Database()
#     db.updateTablesFromS3(aws.s3)
#     res = db.runQuery("SELECT * FROM carpark LIMIT 10;")
#     print(res)
#     print("Done!")


# if __name__ == "__main__":
#     main()
