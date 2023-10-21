import unittest
from raffle_without_db import RaffleRepo


class TestRaffleApp(unittest.TestCase):
    def setUp(self):
        self.raffle_repo = RaffleRepo()

    def test_start_new_draw(self):
        response = self.raffle_repo.start_new_draw()
        self.assertEqual(
            response, "New Raffle draw has been started. Initial pot size: $100"
        )
        latest_draw = self.raffle_repo.get_latest_draw()
        self.assertEqual(latest_draw["pot_amount"], 100)
        self.assertIsNone(latest_draw["winning_numbers"])

    def test_buy_tickets(self):
        self.raffle_repo.start_new_draw()
        response = self.raffle_repo.buy_tickets("Alice", 2)
        self.assertIn("Hi Alice, you have purchased 2 ticket(s)-", response)
        self.assertIn("Ticket 1:", response)
        self.assertIn("Ticket 2:", response)

        # Check pot increase
        latest_draw = self.raffle_repo.get_latest_draw()
        self.assertEqual(latest_draw["pot_amount"], 110)

    def test_run_raffle(self):
        self.raffle_repo.start_new_draw()
        self.raffle_repo.buy_tickets("Alice", 2)
        response = self.raffle_repo.run_raffle()
        self.assertIn("Running Raffle..", response)
        self.assertIn("Winning Ticket is", response)

    def test_multiple_users_tickets(self):
        self.raffle_repo.start_new_draw()
        self.raffle_repo.buy_tickets("Alice", 2)
        self.raffle_repo.buy_tickets("Bob", 1)
        response = self.raffle_repo.run_raffle()
        self.assertIn("Running Raffle..", response)
        self.assertIn("Winning Ticket is", response)


if __name__ == "__main__":
    unittest.main()
