import boto3
import botocore
import os
import dotenv
import base64

dotenv.load_dotenv()

AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY")
REGION_NAME = "us-east-1"

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name= REGION_NAME)

vpc_id = 'vpc-086642ed73a126367'
# Describe security groups
response = ec2.describe_security_groups(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}] if vpc_id else [])
security_group_ids = [group['GroupId'] for group in response['SecurityGroups']]

print("VPC security group IDs:")
for group in response['SecurityGroups']:
    print(f"ID: {group['GroupId']}, Description: {group['Description']}")

# create EC2 instance from an AMI into a specific subnet and with public IP
ami_id = 'ami-0110dd74ac61fe967'              # Innovation Challenge AMI
instance_type = 't2.micro'                    # free tier
key_name = 'prod-ec2-key1'
subnet_id = 'subnet-04b4716667a1b9ba9'
# Define your User Data script
user_data_script = """
#!/bin/bash
echo "Hello, world!" > /tmp/test.txt
"""

# Encode the script in Base64 (optional)
user_data_encoded = base64.b64encode(user_data_script.encode("utf-8")).decode("utf-8")

try:
    response = ec2.run_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType=instance_type,
        KeyName=key_name,
        Monitoring={'Enabled': False},
        NetworkInterfaces=[
            {
                'SubnetId': subnet_id,
                'DeviceIndex': 0,
                'AssociatePublicIpAddress': True
            }
        ],
        UserData=user_data_encoded
    )

    # Get the instance ID from the response
    instance_id = response['Instances'][0]['InstanceId']
    print(f"Instance launched successfully: {instance_id}")

except Exception as e:
    print(f"Error launching instance: {e}")
    exit(1)
security_group_id = 'sg-02d3b51498c3adf5b'  # Web security group

# Add the instance to the security group
try:
    response = ec2.modify_instance_attribute(
        InstanceId=instance_id,
        Groups=[
            security_group_id
        ]
    )

    print(f"Instance {instance_id} added to security group {security_group_id} successfully.")

except Exception as e:
    print(f"Error adding instance to security group: {e}")

# Grant RDS permission to EC2 instance
instance_profile = 'arn:aws:iam::329121819345:instance-profile/RDS_role_for_EC2'
try:
    response = ec2_client.associate_iam_instance_profile(
        IamInstanceProfile={
            'Arn': instance_profile
        },
        InstanceId=instance_id
    )
    print("IAM role attached successfully")
except Exception as e:
    print(f"Error attaching IAM role: {e}")