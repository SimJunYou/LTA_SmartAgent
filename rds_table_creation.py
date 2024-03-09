import boto3
import botocore
import os
import pandas as pd
from sqlalchemy import create_engine, text
import dotenv

dotenv.load_dotenv()

AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
REGION_NAME = "us-east-1"

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION_NAME,
)
rds = session.client("rds")
db_instance_identifier = "db5102-public"

# Describe the RDS instance(s)
try:
    response = rds.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
    db_instance = response["DBInstances"][0]  # Access the first instance in the list
except Exception as e:
    print(f"Error describing DB instance: {e}")
    exit(1)

# Extract endpoint address and port (assuming successful description)
endpoint = db_instance["Endpoint"]["Address"]
port = db_instance["Endpoint"]["Port"]
connection_str = f"postgresql://{DB_USER}:{DB_PASSWORD}@{endpoint}:{port}/{DB_NAME}"