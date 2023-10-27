from datetime import datetime
from functools import wraps
from typing import List, Optional, Callable


class Schedule:
    def __init__(self, schedule_date: datetime, interest: float):
        self.schedule_date = schedule_date
        self.interest = interest

    def to_dict(self):
        return {
            self.schedule_date.strftime("%Y-%m-%d"): round(self.interest, 2),
        }


class RepaymentSchedules:
    def __init__(
        self,
        schedules: List[Schedule],
    ):
        self.schedules = schedules

    def to_dict(self):
        return {
            "schedules": [schedule.to_dict() for schedule in self.schedules],
        }


def pre_check_scheduler(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(
        principal: float,
        irpa: float,
        start_date: str,
        part_payment_date: Optional[str] = None,
        remaining_amount: Optional[float] = None,
        *args,
        **kwargs,
    ) -> dict:
        assert principal > 0, "Principal amount must be a positive number."
        assert irpa >= 0, "interest rate must be a non-negative number."

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            return {
                "error": "ValueError",
                "message": "Invalid start date. Please provide the date in 'YYYY-MM-DD' format.",
            }

        if part_payment_date:
            try:
                part_payment_date = datetime.strptime(part_payment_date, "%Y-%m-%d")
            except ValueError:
                return {
                    "error": "ValueError",
                    "message": "Invalid part payment date. Please provide the date in 'YYYY-MM-DD' format.",
                }

            assert (
                part_payment_date > start_date
            ), "Part payment date must be after the loan start date."
            assert (
                remaining_amount is not None and remaining_amount > 0
            ), "Remaining amount must be a positive number."
            assert (
                remaining_amount < principal
            ), "Remaining amount must be less than the principal amount."

        return func(
            principal,
            irpa,
            start_date,
            part_payment_date,
            remaining_amount,
            *args,
            **kwargs,
        )

    return wrapper
