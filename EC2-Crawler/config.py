import yaml

# Load the YAML configuration file
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

INSTANCE_NAME = config["ec2"]["instance_name"]
AMI_ID = config["ec2"]["ami_id"]
INSTANCE_TYPE = config["ec2"]["instance_type"]
REGION = config["ec2"]["region"]
KEY_NAME = config["ec2"]["key_name"]

SUBNET_ID = config["network"]["subnet_id"]

WEB_URL = config["crawler"]["web_url"]
