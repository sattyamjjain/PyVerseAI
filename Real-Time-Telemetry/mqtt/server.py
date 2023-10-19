import queue
import threading
import time

import paho.mqtt.client as mqtt

from db import MeterValueRepo
from utils import get_logger

_logger = get_logger(__name__)
message_queue = queue.Queue()


def process_messages():
    while True:
        message = message_queue.get()
        if message is None:
            break

        charge_point_id, meter_value = message.split(",", 1)
        MeterValueRepo().add_value(charge_point_id, meter_value)
        _logger.info(f"Processed message for charge point: {charge_point_id}")


def on_message(client, userdata, message):
    payload = message.payload.decode("utf-8")
    _logger.info(f"Received message: {payload}")
    message_queue.put(payload)


client = mqtt.Client("MQTT_Server")
client.on_message = on_message
client.connect("localhost")
client.subscribe("meter_values")
_logger.info("MQTT Server started and subscribed to 'meter_values' topic.")

# Start the message processing thread
threading.Thread(target=process_messages, daemon=True).start()
client.loop_start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    _logger.info("MQTT Server stopped.")
    client.loop_stop()
