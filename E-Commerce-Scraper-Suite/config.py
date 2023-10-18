import yaml

# Load the YAML configuration file
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

DATABASE_URL = config["db"]["url"]
AMAZON_URL_TO_SCRAPE = config["url"]["amazon"]
FLIPKART_URL_TO_SCRAPE = config["url"]["flipkart"]
