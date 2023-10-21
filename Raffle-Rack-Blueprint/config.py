import yaml

# Load the YAML configuration file
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

DATABASE_URL = config["db"]["url"]
