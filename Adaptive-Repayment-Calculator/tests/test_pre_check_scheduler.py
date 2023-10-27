import unittest
from datetime import datetime

from scheduler import pre_check_scheduler


@pre_check_scheduler
def func(
    principal: float,
    irpa: float,
    start_date: datetime,
    part_payment_date: datetime = None,
    remaining_amount: float = None,
):
    return {"status": "success"}


class TestPreCheckScheduler(unittest.TestCase):
    def setUp(self):
        self.valid_principal = 1000
        self.valid_irpa = 10
        self.valid_start_date = "2023-10-10"
        self.valid_part_payment_date = "2023-11-10"
        self.valid_remaining_amount = 900

    def test_valid_input(self):
        result = func(self.valid_principal, self.valid_irpa, self.valid_start_date)
        self.assertEqual(result, {"status": "success"})

    def test_valid_input_with_part_payment(self):
        result = func(
            self.valid_principal,
            self.valid_irpa,
            self.valid_start_date,
            self.valid_part_payment_date,
            self.valid_remaining_amount,
        )
        self.assertEqual(result, {"status": "success"})

    def test_negative_principal(self):
        with self.assertRaises(AssertionError) as context:
            func(-self.valid_principal, self.valid_irpa, self.valid_start_date)
        self.assertEqual(
            str(context.exception), "Principal amount must be a positive number."
        )

    def test_negative_irpa(self):
        with self.assertRaises(AssertionError) as context:
            func(self.valid_principal, -self.valid_irpa, self.valid_start_date)
        self.assertEqual(
            str(context.exception), "interest rate must be a non-negative number."
        )

    def test_invalid_start_date(self):
        result = func(self.valid_principal, self.valid_irpa, "invalid-date")
        self.assertEqual(
            result,
            {
                "error": "ValueError",
                "message": "Invalid start date. Please provide the date in 'YYYY-MM-DD' format.",
            },
        )

    def test_part_payment_before_start(self):
        with self.assertRaises(AssertionError) as context:
            func(
                self.valid_principal,
                self.valid_irpa,
                self.valid_start_date,
                "2023-10-09",
                self.valid_remaining_amount,
            )
        self.assertEqual(
            str(context.exception),
            "Part payment date must be after the loan start date.",
        )

    def test_invalid_part_payment_date(self):
        result = func(
            self.valid_principal,
            self.valid_irpa,
            self.valid_start_date,
            "invalid-date",
            self.valid_remaining_amount,
        )
        self.assertEqual(
            result,
            {
                "error": "ValueError",
                "message": "Invalid part payment date. Please provide the date in 'YYYY-MM-DD' format.",
            },
        )

    def test_negative_remaining_amount(self):
        with self.assertRaises(AssertionError) as context:
            func(
                self.valid_principal,
                self.valid_irpa,
                self.valid_start_date,
                self.valid_part_payment_date,
                -self.valid_remaining_amount,
            )
        self.assertEqual(
            str(context.exception), "Remaining amount must be a positive number."
        )

    def test_remaining_amount_greater_than_principal(self):
        with self.assertRaises(AssertionError) as context:
            func(
                self.valid_principal,
                self.valid_irpa,
                self.valid_start_date,
                self.valid_part_payment_date,
                self.valid_principal + 100,
            )
        self.assertEqual(
            str(context.exception),
            "Remaining amount must be less than the principal amount.",
        )

    def test_missing_remaining_amount(self):
        with self.assertRaises(AssertionError) as context:
            func(
                self.valid_principal,
                self.valid_irpa,
                self.valid_start_date,
                self.valid_part_payment_date,
            )
        self.assertEqual(
            str(context.exception), "Remaining amount must be a positive number."
        )


if __name__ == "__main__":
    unittest.main()
