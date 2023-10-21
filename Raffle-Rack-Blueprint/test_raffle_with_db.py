import unittest
from unittest.mock import patch
from raffle_with_db import RaffleRepo, Draw


class TestRaffleApp(unittest.TestCase):
    def setUp(self):
        self.raffle_repo = RaffleRepo()

    def test_start_new_draw(self):
        with patch.object(self.raffle_repo, "SessionLocal") as mock_session:
            instance = mock_session.return_value
            instance.query.return_value.order_by.return_value.first.return_value = None
            instance.add.return_value = None
            instance.commit.return_value = None
            response = self.raffle_repo.start_new_draw()
            self.assertEqual(
                response, "New Raffle draw has been started. Initial pot size: $100"
            )

    def test_buy_single_ticket(self):
        with patch.object(self.raffle_repo, "SessionLocal") as mock_session:
            instance = mock_session.return_value
            instance.query.return_value.filter_by.return_value.first.return_value = None
            instance.add.return_value = None
            instance.commit.return_value = None
            response = self.raffle_repo.buy_tickets("James", 1)
            self.assertIn("James", response)
            self.assertIn("Ticket 1:", response)

    def test_run_raffle(self):
        with patch.object(self.raffle_repo, "SessionLocal") as mock_session:
            instance = mock_session.return_value
            mock_draw = Draw(pot_amount=100)
            instance.query.return_value.order_by.return_value.first.return_value = (
                mock_draw
            )
            response = self.raffle_repo.run_raffle()
            self.assertIn("Running Raffle..", response)
            self.assertIn("Winning Ticket is", response)


if __name__ == "__main__":
    unittest.main()
