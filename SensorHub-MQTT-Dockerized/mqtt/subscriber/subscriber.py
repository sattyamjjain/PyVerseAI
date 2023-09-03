import paho.mqtt.client as mqtt
from bson import ObjectId
from pymongo import MongoClient
import redis
import json
import logging

BROKER_ADDRESS = "mosquitto"
PORT = 1883
TOPIC_TEMPERATURE = "sensors/temperature"
TOPIC_HUMIDITY = "sensors/humidity"
MONGO_CONNECTION_STRING = "mongodb://mongodb:27017/"

REDIS_PORT = 6379
REDIS_HOST = 'redis'

client = mqtt.Client("Subscriber")
mongo_client = MongoClient(MONGO_CONNECTION_STRING)
db = mongo_client.sensors_database
redis_client = redis.StrictRedis(host='redis', port=6379, db=0)

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)


def on_message(client, userdata, message):
    logging.debug(f"Received message on topic {message.topic}")
    payload = json.loads(message.payload)
    topic = message.topic

    if topic == TOPIC_TEMPERATURE:
        logging.debug("Writing temperature data to MongoDB...")
        db.temperature.insert_one(payload)
        logging.debug("Temperature data written to MongoDB.")
        redis_client.lpush("temperature", json.dumps(payload, cls=JSONEncoder))
        redis_client.ltrim("temperature", 0, 9)
    elif topic == TOPIC_HUMIDITY:
        logging.debug("Writing humidity data to MongoDB...")
        db.humidity.insert_one(payload)
        logging.debug("Humidity data written to MongoDB.")
        redis_client.lpush("humidity", json.dumps(payload, cls=JSONEncoder))
        redis_client.ltrim("humidity", 0, 9)


logging.info("Starting subscriber...")

client.on_message = on_message
logging.info("Connecting to MQTT broker...")
client.connect(BROKER_ADDRESS, PORT)
client.subscribe(TOPIC_TEMPERATURE)
client.subscribe(TOPIC_HUMIDITY)

client.loop_forever()
