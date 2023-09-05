import logging
from datetime import datetime
from typing import List

import pytz
from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
import redis
import json

app = FastAPI()

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

MONGO_CONNECTION_STRING = "mongodb://mongodb:27017/"
REDIS_PORT = 6379
REDIS_HOST = "redis"

db = MongoClient(MONGO_CONNECTION_STRING).sensors_database
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0)

SENSOR_COLLECTION_MAP = {
    "temp_sensor_1": "temperature",
    "humidity_sensor_1": "humidity",
}


def get_datetime_from_millis(ms: int):
    return datetime.fromtimestamp(ms // 1000, tz=pytz.timezone("Asia/Kolkata"))


@app.get("/readings")
def get_readings(sensor_id: str, start_time: str, end_time: str):
    start_date_in_str = get_datetime_from_millis(int(start_time)).isoformat()
    end_date_in_str = get_datetime_from_millis(int(end_time)).isoformat()

    collection_name = SENSOR_COLLECTION_MAP.get(sensor_id)
    if not collection_name:
        raise HTTPException(status_code=400, detail="Invalid sensor_id.")

    readings = list(
        db[collection_name].find(
            {"timestamp": {"$gte": start_date_in_str, "$lte": end_date_in_str}}
        )
    )

    return [
        {
            "id": str(reading["_id"]),
            "sensor_id": reading["sensor_id"],
            "value": reading["value"],
            "timestamp": reading["timestamp"],
        }
        for reading in readings
    ]


@app.get("/latest_readings/{sensor_id}")
def get_latest_readings(sensor_id: str):
    readings_key = SENSOR_COLLECTION_MAP.get(sensor_id)
    if not readings_key:
        raise HTTPException(status_code=400, detail="Invalid sensor_id.")

    readings = redis_client.lrange(readings_key, 0, 9)
    return [json.loads(reading.decode("utf-8")) for reading in readings]
