import logging


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
