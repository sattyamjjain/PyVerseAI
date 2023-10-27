import logging
from datetime import timedelta, datetime
from functools import wraps
from typing import Callable


class InvalidInputException(Exception):
    pass


def last_day_of_month(date):
    return date.replace(
        day=1, month=date.month % 12 + 1, year=date.year + date.month // 12
    ) - timedelta(days=1)


def last_day_of_previous_month(date):
    return date.replace(day=1) - timedelta(days=1)


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


def catch_exp():
    def catcher(f: Callable) -> Callable:
        @wraps(f)
        def _handler(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as exc:
                get_logger(__name__).error(f"{exc.__class__.__name__}: {str(exc)}")
                return {"error": exc.__class__.__name__, "message": str(exc)}

        return _handler

    return catcher


def get_interest(
    principal: float, irpa: float, start_date: datetime, end_date: datetime
):
    leap_year_days = 0
    non_leap_year_days = 0

    for year in range(start_date.year, end_date.year + 1):
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            leap_year_start = max(datetime(year, 1, 1), start_date)
            leap_year_end = min(datetime(year, 12, 31), end_date)
            leap_year_days += (leap_year_end - leap_year_start).days + 1
        else:
            non_leap_year_start = max(datetime(year, 1, 1), start_date)
            non_leap_year_end = min(datetime(year, 12, 31), end_date)
            non_leap_year_days += (non_leap_year_end - non_leap_year_start).days + 1

    time_in_years = (leap_year_days / 366) + (non_leap_year_days / 365)
    return (principal * irpa * time_in_years) / 100
