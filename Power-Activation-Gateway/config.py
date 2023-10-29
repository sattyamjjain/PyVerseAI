import yaml

# Load the YAML configuration file
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

DATABASE_URL = config["db"]["url"]
BROKER_URL = config["celery"]["broker_url"]
CELERY_RESULT_BACKEND = config["celery"]["celery_result_backend"]
