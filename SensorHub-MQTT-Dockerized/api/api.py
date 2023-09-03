import logging
from datetime import datetime

import pytz
from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
import redis
import json

app = FastAPI()

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

MONGO_CONNECTION_STRING = "mongodb://mongodb:27017/"
REDIS_PORT = 6379
REDIS_HOST = 'redis'

mongo_client = MongoClient(MONGO_CONNECTION_STRING)
db = mongo_client.sensors_database
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0)


def get_datetime_from_millis(ms: int):
    return datetime.fromtimestamp(ms // 1000, tz=pytz.timezone('Asia/Kolkata'))


@app.get("/readings")
def get_readings(sensor_id: str, start_time: str, end_time: str):
    start_datetime = get_datetime_from_millis(int(start_time))
    end_datetime = get_datetime_from_millis(int(end_time))
    if sensor_id == "temp_sensor_1":
        readings = db.temperature.find({"timestamp": {"$gte": start_datetime, "$lte": end_datetime}})
        logging.info(readings)
        for reading in readings:
            logging.info("reading", reading)
    elif sensor_id == "humidity_sensor_1":
        readings = db.humidity.find({"timestamp": {"$gte": start_datetime, "$lte": end_datetime}})
        logging.info(readings)
        for reading in readings:
            logging.info("reading", reading)
    else:
        raise HTTPException(status_code=400, detail="Invalid sensor_id.")
    return list(readings)


@app.get("/latest_readings/{sensor_id}")
def get_latest_readings(sensor_id: str):
    if sensor_id == "temp_sensor_1":
        readings = redis_client.lrange("temperature", 0, 9)
    elif sensor_id == "humidity_sensor_1":
        readings = redis_client.lrange("humidity", 0, 9)
    else:
        raise HTTPException(status_code=400, detail="Invalid sensor_id.")
    return [json.loads(reading.decode('utf-8')) for reading in readings]
