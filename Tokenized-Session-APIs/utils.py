import hashlib
import logging
from datetime import datetime
from functools import wraps

import pytz

IST = pytz.timezone('Asia/Kolkata')


def get_datetime_from_millis(ms: int):
    return datetime.fromtimestamp(ms // 1000, tz=IST)


def get_logger(name: str):
    logger = logging.getLogger(name)
    logger.handlers = []
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(threadName)s - %(name)s - %(message)s"
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logging.getLogger(name)


def convert_to_hash(s: str):
    sha256 = hashlib.sha256()
    sha256.update(s.encode())
    return sha256.hexdigest()


def catch_exp():
    def catcher(f):
        @wraps(f)
        def _handler(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                return {"statusCode": 500, "body": {'message': str(e)}}

        return _handler

    return catcher
