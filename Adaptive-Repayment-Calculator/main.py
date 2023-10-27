import argparse
import calendar
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from utils import (
    last_day_of_month,
    last_day_of_previous_month,
    get_logger,
    get_interest,
)
from scheduler import Schedule, RepaymentSchedules, pre_check_scheduler

_TOTAL_MONTH_IN_SCHEDULE = 12
_logger = get_logger(__name__)


def __get_part_interest(
    principal: float,
    remaining_amount: float,
    irpa: float,
    part_payment_date: datetime,
    start_date: datetime,
    end_date: datetime,
):
    _logger.debug("Calculating part payment interest")
    part_payment_interest = get_interest(
        principal,
        irpa,
        start_date,
        part_payment_date - timedelta(days=1),
    )
    return part_payment_interest + get_interest(
        remaining_amount,
        irpa,
        part_payment_date,
        end_date,
    )


@pre_check_scheduler
def generate_repayment_schedule(
    principal: float,
    irpa: float,
    start_date: datetime,
    part_payment_date: datetime = None,
    remaining_amount: float = None,
):
    _logger.info(
        f"Generating repayment schedule for principal {principal} and {irpa}% interest from {start_date.date()}"
    )
    first_payment_date = (
        start_date + relativedelta(months=2, day=7)
        if start_date.day > 10
        else start_date + relativedelta(months=1, day=7)
    )
    end_date = start_date + relativedelta(
        years=1, day=calendar.monthrange(start_date.year + 1, start_date.month)[1]
    )

    schedule_interest = get_interest(
        principal,
        irpa,
        start_date,
        last_day_of_previous_month(first_payment_date),
    )

    if (
        part_payment_date
        and start_date
        <= part_payment_date
        <= last_day_of_previous_month(first_payment_date)
    ):
        _logger.info("Handling part payment before the first schedule date")
        schedule_interest = __get_part_interest(
            principal,
            remaining_amount,
            irpa,
            part_payment_date,
            start_date,
            last_day_of_previous_month(first_payment_date),
        )
        principal = remaining_amount

    repayment_schedules = [
        Schedule(
            schedule_date=first_payment_date,
            interest=schedule_interest,
        )
    ]

    current_date = first_payment_date
    while current_date <= end_date:
        _logger.debug(f"Processing date: {current_date}")
        schedule_interest = get_interest(
            principal,
            irpa,
            current_date.replace(day=1),
            last_day_of_month(current_date),
        )
        if part_payment_date and current_date.replace(
            day=1
        ) <= part_payment_date <= last_day_of_month(current_date):
            _logger.info("Handling part payment")
            schedule_interest = __get_part_interest(
                principal,
                remaining_amount,
                irpa,
                part_payment_date,
                current_date.replace(day=1),
                last_day_of_month(current_date),
            )
            principal = remaining_amount

        if len(repayment_schedules) == (
            _TOTAL_MONTH_IN_SCHEDULE - 1
            if start_date.day > 10
            else _TOTAL_MONTH_IN_SCHEDULE
        ):
            repayment_schedules.append(
                Schedule(
                    schedule_date=last_day_of_month(current_date),
                    interest=schedule_interest + principal,
                )
            )
        else:
            repayment_schedules.append(
                Schedule(
                    schedule_date=current_date + relativedelta(months=1),
                    interest=schedule_interest,
                )
            )
        current_date += relativedelta(months=1)
    return RepaymentSchedules(schedules=repayment_schedules)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate repayment schedule.")
    parser.add_argument(
        "--principal", type=float, help="The principal loan amount", default=10000
    )
    parser.add_argument(
        "--irpa",
        type=float,
        help="The interest rate per annum (as a percentage)",
        default=12,
    )
    parser.add_argument(
        "--start_date",
        type=str,
        help="The start date of the loan (in YYYY-MM-DD format)",
        default="2023-10-24",
    )
    parser.add_argument(
        "--part_payment_date",
        type=str,
        help="The date of the part payment (in YYYY-MM-DD format)",
        required=False,
    )
    parser.add_argument(
        "--remaining_amount",
        type=float,
        help="The remaining loan amount after the part payment",
        required=False,
    )

    _args = parser.parse_args()
    try:
        repayment_schedule = generate_repayment_schedule(
            _args.principal,
            _args.irpa,
            _args.start_date,
            _args.part_payment_date,
            _args.remaining_amount,
        )
        _logger.info("Repayment schedule generated successfully")
        _logger.info(repayment_schedule.to_dict())
    except Exception as exc:
        _logger.error(f"An error occurred: {exc.__class__.__name__}: {str(exc)}")
