import random

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Float,
)
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import pytz
from config import DATABASE_URL

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True)


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    ticket_numbers = Column(String, nullable=False)  # Storing as comma-separated string


class Draw(Base):
    __tablename__ = "draws"

    draw_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pot_amount = Column(Float, nullable=False)
    winning_numbers = Column(String, nullable=True)
    draw_date = Column(
        DateTime, default=lambda: datetime.now(pytz.timezone("Asia/Kolkata"))
    )


class Prize(Base):
    __tablename__ = "prizes"

    prize_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    draw_id = Column(Integer, ForeignKey("draws.draw_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    prize_amount = Column(Float, nullable=False)
    prize_group = Column(String, nullable=False)


# Setting up the database engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class RaffleRepo:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_all_tables(self):
        Base.metadata.create_all(bind=self.engine)

    def drop_all_tables(self):
        Base.metadata.drop_all(bind=self.engine)

    def start_new_draw(self):
        session = self.SessionLocal()
        new_draw = Draw(pot_amount=100, winning_numbers=None)
        session.add(new_draw)
        session.commit()
        session.close()
        return "New Raffle draw has been started. Initial pot size: $100"

    def get_latest_draw(self):
        session = self.SessionLocal()
        draw = session.query(Draw).order_by(Draw.draw_id.desc()).first()
        session.close()
        return draw

    def buy_tickets(self, user_name, number_of_tickets):
        session = self.SessionLocal()

        # Check if user exists or create a new one
        user = session.query(User).filter_by(name=user_name).first()
        if not user:
            user = User(name=user_name)
            session.add(user)
            session.commit()

        # Generate tickets
        ticket_strings = []
        for i in range(number_of_tickets):
            ticket_numbers = sorted(random.sample(range(1, 16), 5))
            ticket = Ticket(
                user_id=user.user_id, ticket_numbers=" ".join(map(str, ticket_numbers))
            )
            session.add(ticket)
            ticket_strings.append(
                f"Ticket {i + 1}: {' '.join(map(str, ticket_numbers))}"
            )

        # Update draw pot amount
        draw = session.query(Draw).order_by(Draw.draw_id.desc()).first()
        if draw:
            draw.pot_amount += number_of_tickets * 5
        session.commit()
        session.close()

        return (
            f"Hi {user_name}, you have purchased {number_of_tickets} ticket(s)-\n"
            + "\n".join(ticket_strings)
        )

    def run_raffle(self):
        session = self.SessionLocal()

        # Generate the winning ticket
        winning_numbers = sorted(random.sample(range(1, 16), 5))

        # Fetch the latest draw details and tickets
        draw = session.query(Draw).order_by(Draw.draw_id.desc()).first()
        draw.winning_numbers = " ".join(map(str, winning_numbers))
        session.commit()
        all_tickets = session.query(Ticket).all()

        winners = {2: [], 3: [], 4: [], 5: []}

        # Compare purchased tickets with winning ticket
        for ticket in all_tickets:
            matched_numbers = len(
                set(ticket.ticket_numbers.split()).intersection(
                    set(map(str, winning_numbers))
                )
            )
            if matched_numbers >= 2:
                winners[matched_numbers].append(ticket)

        # Calculate rewards and display winners
        pot_amount = draw.pot_amount
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
                user = session.query(User).filter_by(user_id=ticket.user_id).first()
                output += (
                    f"{user.name} with 1 winning ticket(s)- ${reward_per_ticket:.2f}\n"
                )
            if not tickets:
                output += "Nil\n"
            output += "\n"

        session.close()
        return output
