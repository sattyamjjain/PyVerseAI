import unittest
from main import generate_repayment_schedule


class TestScheduleGenerationWithPartPayment(unittest.TestCase):
    def setUp(self):
        self.principal = 10000
        self.irpa = 12

    def test_part_payment_in_first_month(self):
        start_date = "2023-01-01"
        part_payment_date = "2023-01-15"
        remaining_amount = 5000
        repayment_schedule = generate_repayment_schedule(
            self.principal, self.irpa, start_date, part_payment_date, remaining_amount
        )
        expected_schedules = [
            {"2023-02-07": 101.92},
            {"2023-03-07": 92.05},
            {"2023-04-07": 101.92},
            {"2023-05-07": 98.63},
            {"2023-06-07": 101.92},
            {"2023-07-07": 98.63},
            {"2023-08-07": 101.92},
            {"2023-09-07": 101.92},
            {"2023-10-07": 98.63},
            {"2023-11-07": 101.92},
            {"2023-12-07": 98.63},
            {"2024-01-07": 101.92},
            {"2024-01-31": 10101.64},
        ]
        self.assertEqual(repayment_schedule.to_dict()["schedules"], expected_schedules)

    def test_part_payment_in_middle_month(self):
        start_date = "2023-01-01"
        part_payment_date = "2023-06-15"
        remaining_amount = 5000
        repayment_schedule = generate_repayment_schedule(
            self.principal, self.irpa, start_date, part_payment_date, remaining_amount
        )
        expected_schedules = [
            {"2023-02-07": 101.92},
            {"2023-03-07": 92.05},
            {"2023-04-07": 101.92},
            {"2023-05-07": 98.63},
            {"2023-06-07": 101.92},
            {"2023-07-07": 72.33},
            {"2023-08-07": 50.96},
            {"2023-09-07": 50.96},
            {"2023-10-07": 49.32},
            {"2023-11-07": 50.96},
            {"2023-12-07": 49.32},
            {"2024-01-07": 50.96},
            {"2024-01-31": 5050.82},
        ]
        self.assertEqual(repayment_schedule.to_dict()["schedules"], expected_schedules)

    def test_part_payment_in_last_month(self):
        start_date = "2023-01-01"
        part_payment_date = "2023-12-15"
        remaining_amount = 5000
        repayment_schedule = generate_repayment_schedule(
            self.principal, self.irpa, start_date, part_payment_date, remaining_amount
        )
        expected_schedules = [
            {"2023-02-07": 101.92},
            {"2023-03-07": 92.05},
            {"2023-04-07": 101.92},
            {"2023-05-07": 98.63},
            {"2023-06-07": 101.92},
            {"2023-07-07": 98.63},
            {"2023-08-07": 101.92},
            {"2023-09-07": 101.92},
            {"2023-10-07": 98.63},
            {"2023-11-07": 101.92},
            {"2023-12-07": 98.63},
            {"2024-01-07": 73.97},
            {"2024-01-31": 5050.82},
        ]
        self.assertEqual(repayment_schedule.to_dict()["schedules"], expected_schedules)

    def test_part_payment_in_leap_year(self):
        start_date = "2024-01-01"
        part_payment_date = "2024-06-15"
        remaining_amount = 5000
        repayment_schedule = generate_repayment_schedule(
            self.principal, self.irpa, start_date, part_payment_date, remaining_amount
        )
        print(repayment_schedule.to_dict()["schedules"])
        expected_schedules = [
            {"2024-02-07": 101.64},
            {"2024-03-07": 95.08},
            {"2024-04-07": 101.64},
            {"2024-05-07": 98.36},
            {"2024-06-07": 101.64},
            {"2024-07-07": 72.13},
            {"2024-08-07": 50.82},
            {"2024-09-07": 50.82},
            {"2024-10-07": 49.18},
            {"2024-11-07": 50.82},
            {"2024-12-07": 49.18},
            {"2025-01-07": 50.82},
            {"2025-01-31": 5050.96},
        ]
        self.assertEqual(repayment_schedule.to_dict()["schedules"], expected_schedules)


if __name__ == "__main__":
    unittest.main()
