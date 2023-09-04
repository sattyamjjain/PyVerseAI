import random
import boto3
from botocore.exceptions import ClientError

import config
import utils

# Initialize logger for the current module
_logger = utils.get_logger(__name__)

# Create a boto3 session with the specified AWS profile
session = boto3.Session(profile_name="secondary")

# Initialize the EC2 client for the specified region
ec2_client = session.client("ec2", region_name=config.REGION)


def get_key_pairs():
    """
    Retrieve a list of existing key pairs.

    Returns:
    - list: A list of key pair names.
    """
    try:
        return [
            key_pair["KeyName"]
            for key_pair in ec2_client.describe_key_pairs()["KeyPairs"]
        ]
    except ClientError as e:
        _logger.error(f"Error fetching key pairs: {e}")
        return []


def create_key_pair(key_name: str):
    """
    Create a new EC2 key pair.

    Args:
    - key_name (str): Name of the new key pair.

    Returns:
    - str: Name of the created key pair or None in case of error.
    """
    try:
        response = ec2_client.create_key_pair(KeyName=key_name)
        private_key = response["KeyMaterial"]
        with open(f"{key_name}.pem", "w") as key_file:
            key_file.write(private_key)
        return key_name
    except ClientError as e:
        _logger.error(f"Error creating key pair: {e}")
        return None


def launch_new_instance():
    """
    Launch a new EC2 instance.

    The instance will be associated with a key pair (either existing or new).
    """
    try:
        ec2_resource = session.resource("ec2", region_name=config.REGION)
        key_pairs = get_key_pairs()
        key_name = (
            random.choice(key_pairs) if key_pairs else create_key_pair(config.KEY_NAME)
        )

        instance = ec2_resource.create_instances(
            ImageId=config.AMI_ID,
            MinCount=1,
            MaxCount=1,
            InstanceType=config.INSTANCE_TYPE,
            KeyName=key_name,
            NetworkInterfaces=[
                {
                    "DeviceIndex": 0,
                    "AssociatePublicIpAddress": True,
                    "SubnetId": config.SUBNET_ID,
                }
            ],
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [{"Key": "Name", "Value": config.INSTANCE_NAME}],
                }
            ],
        )[0]
        _logger.info(
            f"Instance {instance.id} created with state {instance.state['Name']} using key pair {key_name}"
        )
    except ClientError as e:
        _logger.error(f"Error launching EC2 instance: {e}")


def start_instance(instance_id: str):
    """
    Start the specified EC2 instance.

    Args:
    - instance_id (str): ID of the EC2 instance to start.
    """
    try:
        response = ec2_client.start_instances(InstanceIds=[instance_id])
        for instance in response["StartingInstances"]:
            _logger.info(
                f"Started instance {instance['InstanceId']} which was in state {instance['PreviousState']['Name']} and is now in state {instance['CurrentState']['Name']}"
            )
    except ClientError as e:
        _logger.error(f"Error starting EC2 instance {instance_id}: {e}")


def stop_instance(instance_id: str):
    """
    Stop the specified EC2 instance.

    Args:
    - instance_id (str): ID of the EC2 instance to stop.
    """
    try:
        response = ec2_client.stop_instances(InstanceIds=[instance_id])
        for instance in response["StoppingInstances"]:
            _logger.info(
                f"Stopping instance {instance['InstanceId']} which was in state {instance['PreviousState']['Name']} and is transitioning to state {instance['CurrentState']['Name']}"
            )
    except ClientError as e:
        _logger.error(f"Error stopping EC2 instance {instance_id}: {e}")
