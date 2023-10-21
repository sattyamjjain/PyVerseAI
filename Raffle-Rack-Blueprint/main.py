import raffle_with_db
import raffle_without_db


def exec_raffle_rack_using_db():
    raffle_repo = raffle_with_db.RaffleRepo()

    while True:
        print("Welcome to My Raffle App")

        # Display draw status
        draw = raffle_repo.get_latest_draw()
        if draw:
            print(f"Status: Draw is ongoing. Raffle pot size is ${draw.pot_amount}")
        else:
            print("Status: Draw has not started")

        print("[1] Start a New Draw")
        print("[2] Buy Tickets")
        print("[3] Run Raffle")

        choice = input("Enter your choice: ")

        if choice == "1":
            print(raffle_repo.start_new_draw())
        elif choice == "2":
            user_input = input("Enter your name, no of tickets to purchase: ")
            user_name, number_of_tickets = user_input.split(",")
            print(raffle_repo.buy_tickets(user_name, int(number_of_tickets)))
        elif choice == "3":
            print(raffle_repo.run_raffle())

        input("Press any key to return to main menu")


def exec_raffle_rack_without_using_db():
    raffle_repo = raffle_without_db.RaffleRepo()

    while True:
        print("Welcome to My Raffle App")

        # Display draw status
        draw = raffle_repo.get_latest_draw()
        if draw:
            print(f"Status: Draw is ongoing. Raffle pot size is ${draw['pot_amount']}")
        else:
            print("Status: Draw has not started")

        print("[1] Start a New Draw")
        print("[2] Buy Tickets")
        print("[3] Run Raffle")

        choice = input("Enter your choice: ")

        if choice == "1":
            print(raffle_repo.start_new_draw())
        elif choice == "2":
            user_input = input("Enter your name, no of tickets to purchase: ")
            user_name, number_of_tickets = user_input.split(",")
            print(raffle_repo.buy_tickets(user_name, int(number_of_tickets)))
        elif choice == "3":
            print(raffle_repo.run_raffle())

        input("Press any key to return to main menu")


if __name__ == "__main__":
    # exec_raffle_rack_using_db()
    exec_raffle_rack_without_using_db()
