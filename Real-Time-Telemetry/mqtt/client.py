import pandas as pd
import paho.mqtt.client as mqtt
import time
from utils import get_logger

_logger = get_logger(__name__)

csv_path = "./meter_values_dump_10k.csv"
df = pd.read_csv(csv_path)


def mock_client(charge_point_id, payload):
    client = mqtt.Client(charge_point_id)
    client.connect("localhost")
    _logger.info(f"Mock client {charge_point_id} connected to broker.")
    time.sleep(5)
    client.publish("meter_values", f"{charge_point_id},{payload}")
    _logger.info(f"Mock client {charge_point_id} published payload: {payload}")


for _, row in df.head(10).iterrows():
    mock_client(row["charge_point_id"], row["payload"])
