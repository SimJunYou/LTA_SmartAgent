import time
import boto3
import os
import dotenv
import base64
import pandas as pd

import utils.account_constants as cst

dotenv.load_dotenv()

AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
REGION_NAME = "us-east-1"


class AWS:
    def __init__(self):
        self.session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=REGION_NAME,
        )
        self.ec2 = self.EC2(self.session)
        self.s3 = self.S3(self.session)
        self.rds = self.RDS(self.session, self.s3)

    def start(self):
        # Start EC2
        self.ec2.startInstance(cst.EC2_INSTANCE_ID)
        print("Starting EC2...")

        # Start RDS
        self.rds.createInstance()
        print("Starting RDS...")
        # TODO: Run rds.createTable and updateTable after rds is ready

    def stop(self):
        # Delete and stop RDS
        print("Deleting RDS...")
        self.rds.deleteInstance(cst.DB_SUBNET_GROUP_NAME)
        print("Deleted RDS")

        # Stop EC2
        self.ec2.stopInstance(cst.EC2_INSTANCE_ID)
        # self.ec2.terminateInstance(cst.EC2_INSTANCE_ID)
        print("Stopped EC2")

    class EC2:
        def __init__(self, session):
            self.ec2 = session.client("ec2")

        def listInstance(self):
            # List existing EC2 instances with public IP addresses
            try:
                response = self.ec2.describe_instances()
                instances = response["Reservations"]
                for reservation in instances:
                    for instance in reservation["Instances"]:
                        instance_id = instance["InstanceId"]
                        state = instance["State"]["Name"]
                        public_ip = instance.get("PublicIpAddress", "N/A")
                        print(
                            f"Instance ID: {instance_id}, State: {state}, Public IP: {public_ip}"
                        )
            except Exception as e:
                print(f"Error listing instances: {e}")

        def stopInstance(self, instance_id):
            # Stop EC2 instance of specified ID
            try:
                response = self.ec2.stop_instances(InstanceIds=[instance_id])
                print("Instance stopped successfully")
            except Exception as e:
                print(f"Error stopping instance: {e}")

        def startInstance(self, instance_id):
            # Start EC2 instance of specified ID
            try:
                response = self.ec2.start_instances(InstanceIds=[instance_id])
                print("Instance started successfully")
            except Exception as e:
                print(f"Error starting instance: {e}")

        def createInstance(
            self,
            user_data_script=None,
            ami_id=cst.AMI_ID,
            subnet_id=cst.SUBNET_ID1,
            key_name=cst.KEY_NAME,
        ):
            # Create EC2 instance from an AMI into a specific subnet and with public IP

            # TODO: Write user data script with automatic git pull
            # Define your User Data script
            user_data_script = """
            #!/bin/bash
            # chkconfig: 2345 90 10
            # description: startup script for RouteWise bot (DBA5102 Innovation Challenge)
            exec &>> /var/log/startup_script.log
            echo "[$(date)] Starting RouteWise bot startup script"
            # Switch to the ec2-user 
            su - ec2-user -c "
            echo '[$(date)] Switched to ec2-user'
            # Change directory
            cd /home/ec2-user/LTA_SmartAgent
            echo '[$(date)] Pulling latest changes from Git'
            git pull
            echo '[$(date)] Initializing conda'
            conda init
            echo '[$(date)] Activating conda environment'
            conda activate dba5102
            echo '[$(date)] Installing Python dependencies'
            pip install pandas numpy bs4 langchain langchain-experimental langchain-openai python-telegram-bot python-dotenv tabulate boto3 sqlalchemy psycopg2-binary
            echo '[$(date)] Running Python bot'
            python bot.py
            "
            echo "[$(date)] RouteWise bot startup script completed"
            """

            # Encode the script in Base64 (optional)
            user_data_encoded = base64.b64encode(
                user_data_script.encode("utf-8")
            ).decode("utf-8")

            # Launch the EC2 instance with User Data

            instance_type = "t2.micro"  # free tier

            try:
                response = self.ec2.run_instances(
                    ImageId=ami_id,
                    MinCount=1,
                    MaxCount=1,
                    InstanceType=instance_type,
                    KeyName=key_name,
                    Monitoring={"Enabled": False},
                    NetworkInterfaces=[
                        {
                            "SubnetId": subnet_id,
                            "DeviceIndex": 0,
                            "AssociatePublicIpAddress": True,
                        }
                    ],
                    UserData=user_data_encoded,
                )

                # Get the instance ID from the response
                instance_id = response["Instances"][0]["InstanceId"]
                print(f"Instance launched successfully: {instance_id}")

            except Exception as e:
                print(f"Error launching instance: {e}")
                exit(1)

        def modifyInstance(
            self,
            instance_id,
            security_group_id=cst.SECURITY_GROUP_ID,
            instance_profile=cst.INSTANCE_PROFILE,
        ):
            try:
                # Add the instance to the security group
                response = self.ec2.modify_instance_attribute(
                    InstanceId=instance_id, Groups=[security_group_id]
                )

                print(
                    f"Instance {instance_id} added to security group {security_group_id} successfully."
                )

            except Exception as e:
                print(f"Error adding instance to security group: {e}")

            # Attach IAM role to the instance
            try:
                response = self.ec2.associate_iam_instance_profile(
                    IamInstanceProfile={"Arn": instance_profile}, InstanceId=instance_id
                )
                print("IAM role attached successfully")
            except Exception as e:
                print(f"Error attaching IAM role: {e}")

        def terminateInstance(self, instance_id):
            # Terminate EC2 instance of specified ID
            try:
                # Terminate the instance
                response = self.ec2.terminate_instances(InstanceIds=[instance_id])

                print(f"Instance {instance_id} terminated successfully.")

            except Exception as e:
                print(f"Error terminating instance: {e}")

    class S3:
        def __init__(self, session):
            self.s3 = session.client("s3")

        def listBucket(self):
            bucket_list = self.s3.list_buckets()
            # Output the bucket names
            print("Existing buckets:")
            for bucket in bucket_list["Buckets"]:
                print(f'  {bucket["Name"]}')

        def listObject(self, bucket_name):
            response = self.s3.list_objects(Bucket=bucket_name)
            try:
                keys = [content["Key"] for content in response["Contents"]]
                print(keys)
                return keys
            except Exception as e:
                print("Error listing, bucket may be empty")

        def readObject(self, bucket_name, key):
            # Read a CSV
            file_key = key
            df = pd.read_csv(
                self.s3.get_object(Bucket=bucket_name, Key=file_key)["Body"],
                encoding="utf-8",
            )
            return df

        def upload(self, bucket_name, file_to_upload, output_filename):
            # Upload a csv
            with open(file_to_upload, "rb") as f:  # Open the file in binary read mode
                self.s3.put_object(
                    Body=f,  # Read the file's contents
                    Bucket=bucket_name,
                    Key=output_filename,
                )

            print(f"File uploaded to S3://{bucket_name}/{output_filename}")

    class RDS:
        def __init__(self, session, s3):
            self.rds = session.client("rds")
            self.s3 = s3

        def listInstance(self):
            # List existing RDS instances
            instance_ids = []
            try:
                response = self.rds.describe_db_instances()
                instances = response["DBInstances"]
                for instance in instances:
                    instance_id = instance["DBInstanceIdentifier"]
                    instance_status = instance["DBInstanceStatus"]
                    print(f"Instance ID: {instance_id}, Status: {instance_status}")
                    instance_ids.append(instance_id)
                return instance_ids
            except Exception as e:
                print(f"Error listing RDS instances: {e}")

        def readInstance(self, instance_id="db5102-public"):
            # Describe the RDS instance(s)
            try:
                response = self.rds.describe_db_instances(
                    DBInstanceIdentifier=instance_id
                )
                db_instance = response["DBInstances"][
                    0
                ]  # Access the first instance in the list

                # Extract endpoint address and port (assuming successful description)
                endpoint = db_instance["Endpoint"]["Address"]
                port = db_instance["Endpoint"]["Port"]

                # print(f"RDS endpoint and port: {endpoint}:{port}")
                return endpoint, port
            except Exception as e:
                print(f"Error describing DB instance: {e}")
                return None, None

        def deleteInstance(
            self,
            db_subnet_group_name=cst.DB_SUBNET_GROUP_NAME,
            instance_id="db5102-public",
        ):
            # Delete the DB instance
            try:
                response = self.rds.delete_db_instance(
                    DBInstanceIdentifier=instance_id,
                    SkipFinalSnapshot=True,
                    # FinalDBSnapshotIdentifier='string',
                    DeleteAutomatedBackups=True,
                )
                print(response)
            except Exception as e:
                print(e)

            timeout = 0
            while instance_id in self.rdsListInstance():
                if timeout == 10:
                    print("Timeout waiting for RDS deletion")
                    return
                time.sleep(30)
                timeout += 1

            # Delete the DB subnet group
            try:
                response = self.rds.delete_db_subnet_group(
                    DBSubnetGroupName=db_subnet_group_name
                )
                print("DB subnet group deleted successfully")
            except Exception as e:
                print(f"Error deleting DB subnet group: {e}")

        def createInstance(
            self,
            db_subnet_group_name=cst.DB_SUBNET_GROUP_NAME,
            subnet_ids=[cst.SUBNET_ID1, cst.SUBNET_ID2],
            security_group_id_rds=cst.SECURITY_GROUP_ID_RDS,
        ):
            response = self.rds.create_db_subnet_group(
                DBSubnetGroupName=db_subnet_group_name,
                DBSubnetGroupDescription="LTA Innovation Challenge DB public subnet group",  # public or private
                SubnetIds=subnet_ids,
            )

            subnet_success = response["ResponseMetadata"]["HTTPStatusCode"] == 200
            if not subnet_success:
                print("Error creating RDS subnet")
                return

            # Create a RDS PostGres within free tier
            response = self.rds.create_db_instance(
                DBName=DB_NAME,
                DBInstanceIdentifier="db5102-public",
                AllocatedStorage=20,
                DBInstanceClass="db.t3.micro",
                Engine="postgres",
                MasterUsername=DB_USER,
                MasterUserPassword=DB_PASSWORD,
                VpcSecurityGroupIds=[
                    security_group_id_rds,
                ],
                AvailabilityZone="us-east-1a",
                DBSubnetGroupName=db_subnet_group_name,
                BackupRetentionPeriod=1,
                Port=5432,
                EngineVersion="16.2",
                AutoMinorVersionUpgrade=True,
                LicenseModel="postgresql-license",
                PubliclyAccessible=True,  # Public or private
                StorageType="gp2",
                EnablePerformanceInsights=False,
                DeletionProtection=False,
                MaxAllocatedStorage=20,
            )
            print(response)


if __name__ == "__main__":
    aws = AWS()
    # print("creating EC2 and RDS instances...")
    # aws.start()
    # print("done!")
    aws.ec2.listInstance()
