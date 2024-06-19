import yaml

# Load the YAML configuration file
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

OPENAI_API_KEY = config["openai"]["api_key"]
OPENAI_MODEL = config["openai"]["model"]

LOGGING_FILE = config["logging"]["file"]

SAMPLE_INPUT_FILES_PATH = config["paths"]["input_dir"]
SAMPLE_OUTPUT_FILES_PATH = config["paths"]["output_dir"]
