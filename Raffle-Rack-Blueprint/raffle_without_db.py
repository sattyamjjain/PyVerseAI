import random


class RaffleRepo:
    def __init__(self):
        self.users = {}
        self.tickets = []
        self.draws = []
        self.prizes = []

    def start_new_draw(self):
        self.tickets = []
        self.prizes = []
        self.draws.append({"pot_amount": 100, "winning_numbers": None})
        return "New Raffle draw has been started. Initial pot size: $100"

    def get_latest_draw(self):
        if self.draws:
            return self.draws[-1]
        return None

    def buy_tickets(self, user_name, number_of_tickets):
        if user_name not in self.users:
            self.users[user_name] = []

        ticket_strings = []
        for i in range(number_of_tickets):
            ticket_numbers = sorted(random.sample(range(1, 16), 5))
            self.tickets.append(
                {"user_name": user_name, "ticket_numbers": ticket_numbers}
            )
            ticket_strings.append(
                f"Ticket {i + 1}: {' '.join(map(str, ticket_numbers))}"
            )

        # Update draw pot amount
        latest_draw = self.get_latest_draw()
        if latest_draw:
            latest_draw["pot_amount"] += number_of_tickets * 5

        return (
            f"Hi {user_name}, you have purchased {number_of_tickets} ticket(s)-\n"
            + "\n".join(ticket_strings)
        )

    def run_raffle(self):
        winning_numbers = sorted(random.sample(range(1, 16), 5))

        winners = {2: [], 3: [], 4: [], 5: []}

        # Compare purchased tickets with winning ticket
        for ticket in self.tickets:
            matched_numbers = len(
                set(ticket["ticket_numbers"]).intersection(set(winning_numbers))
            )
            if matched_numbers >= 2:
                winners[matched_numbers].append(ticket)

        # Calculate rewards and display winners
        latest_draw = self.get_latest_draw()
        pot_amount = latest_draw["pot_amount"]
        rewards = {
            2: 0.1 * pot_amount,
            3: 0.15 * pot_amount,
            4: 0.25 * pot_amount,
            5: 0.5 * pot_amount,
        }
        output = f"Running Raffle..\nWinning Ticket is {' '.join(map(str, winning_numbers))}\n\n"

        for group, tickets in winners.items():
            reward_per_ticket = rewards[group] / len(tickets) if tickets else 0
            output += f"Group {group} Winners:\n"
            for ticket in tickets:
                output += f"{ticket['user_name']} with 1 winning ticket(s)- ${reward_per_ticket:.2f}\n"
            if not tickets:
                output += "Nil\n"
            output += "\n"

        return output
