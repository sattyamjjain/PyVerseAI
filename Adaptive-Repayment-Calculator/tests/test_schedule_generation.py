import unittest
from main import generate_repayment_schedule


class TestScheduleGeneration(unittest.TestCase):
    def test_start_date_beginning_of_month(self):
        principal = 10000
        irpa = 12
        start_date = "2023-10-1"
        repayment_schedule = generate_repayment_schedule(principal, irpa, start_date)
        expected_schedules = [
            {"2023-11-07": 101.92},
            {"2023-12-07": 98.63},
            {"2024-01-07": 101.92},
            {"2024-02-07": 101.64},
            {"2024-03-07": 95.08},
            {"2024-04-07": 101.64},
            {"2024-05-07": 98.36},
            {"2024-06-07": 101.64},
            {"2024-07-07": 98.36},
            {"2024-08-07": 101.64},
            {"2024-09-07": 101.64},
            {"2024-10-07": 98.36},
            {"2024-10-31": 10101.64},
        ]
        self.assertEqual(repayment_schedule.to_dict()["schedules"], expected_schedules)

    def test_start_date_end_of_month(self):
        principal = 10000
        irpa = 12
        start_date = "2023-01-31"
        repayment_schedule = generate_repayment_schedule(principal, irpa, start_date)
        expected_schedules = [
            {"2023-03-07": 95.34},
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

    def test_start_date_in_leap_year(self):
        principal = 10000
        irpa = 12
        start_date = "2024-06-15"
        repayment_schedule = generate_repayment_schedule(principal, irpa, start_date)
        expected_schedules = [
            {"2024-08-07": 154.1},
            {"2024-09-07": 101.64},
            {"2024-10-07": 98.36},
            {"2024-11-07": 101.64},
            {"2024-12-07": 98.36},
            {"2025-01-07": 101.64},
            {"2025-02-07": 101.92},
            {"2025-03-07": 92.05},
            {"2025-04-07": 101.92},
            {"2025-05-07": 98.63},
            {"2025-06-07": 101.92},
            {"2025-06-30": 10098.63},
        ]
        self.assertEqual(repayment_schedule.to_dict()["schedules"], expected_schedules)

    def test_loan_spanning_over_leap_year(self):
        principal = 10000
        irpa = 12
        start_date = "2023-12-15"
        repayment_schedule = generate_repayment_schedule(principal, irpa, start_date)
        expected_schedules = [
            {"2024-02-07": 157.53},
            {"2024-03-07": 95.08},
            {"2024-04-07": 101.64},
            {"2024-05-07": 98.36},
            {"2024-06-07": 101.64},
            {"2024-07-07": 98.36},
            {"2024-08-07": 101.64},
            {"2024-09-07": 101.64},
            {"2024-10-07": 98.36},
            {"2024-11-07": 101.64},
            {"2024-12-07": 98.36},
            {"2024-12-31": 10101.64},
        ]
        self.assertEqual(repayment_schedule.to_dict()["schedules"], expected_schedules)


if __name__ == "__main__":
    unittest.main()
