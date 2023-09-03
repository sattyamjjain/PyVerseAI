import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
import random
import logging

BROKER_ADDRESS = "mosquitto"
PORT = 1883
TOPIC_TEMPERATURE = "sensors/temperature"
TOPIC_HUMIDITY = "sensors/humidity"


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def generate_sensor_reading(sensor_id):
    logging.debug(f"Generating sensor reading for {sensor_id}")
    reading_value = random.randint(20, 30) if sensor_id == "temp_sensor_1" else random.randint(50, 70)
    return json.dumps({
        "sensor_id": sensor_id,
        "value": reading_value,
        "timestamp": datetime.now().isoformat()
    })


client = mqtt.Client("Publisher")
logging.info("Connecting to MQTT broker...")
client.connect(BROKER_ADDRESS, PORT)

logging.info("Starting publisher...")

while True:
    temperature_reading = generate_sensor_reading("temp_sensor_1")
    humidity_reading = generate_sensor_reading("humidity_sensor_1")

    logging.debug(f"Publishing to {TOPIC_TEMPERATURE}: {temperature_reading}")
    client.publish(TOPIC_TEMPERATURE, temperature_reading)

    logging.debug(f"Publishing to {TOPIC_HUMIDITY}: {humidity_reading}")
    client.publish(TOPIC_HUMIDITY, humidity_reading)

    time.sleep(10)
