from aws import AWS
import pandas as pd

def upload_to_s3(table_name, data):
    s3 = AWS().s3
    output_file = table_name + ".csv"
    # Check if the file exists
    file_exists = output_file in s3.listObject('dba5102')
    print("File exists:", file_exists)
    
    if file_exists:
        # File exists, download, append to it, then upload new
        print("Appending to s3", output_file)
        df = s3.readObject('dba5102', output_file)
        df = pd.concat([df, data], axis=0, ignore_index=True)
        df.to_csv(output_file, index=False)
        s3.upload('dba5102', output_file, output_file)
    else:
        # File does not exist, create a new one
        print("Creating new", output_file)
        data.to_csv(output_file, index=False)
        s3.upload('dba5102', output_file, output_file)

def download_local(table_name):
    pass

def download_s3(table_name):
    pass

def download_all_s3():
    table_names = []
    for table_name in table_names:
        download_s3(table_name)

def parse_api_json(table_name):
    pass