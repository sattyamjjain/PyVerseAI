import yaml

# Load the YAML configuration file
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

MONGO_CONNECTION_STRING = config["mongodb"]["conn_str"]
