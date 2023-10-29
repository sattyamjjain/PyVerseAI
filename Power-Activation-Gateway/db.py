import uuid
from enum import Enum

import pytz
from sqlalchemy import create_engine, Column, String, DateTime, UUID
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL
from datetime import datetime
from utils import get_logger

_logger = get_logger(__name__)
Base = declarative_base()


class PowerActivationStatus(Enum):
    ACTIVATED = "ACTIVATED"
    DEACTIVATED = "DEACTIVATED"


class PowerActivation(Base):
    __tablename__ = "power_activation"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    stone_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    activation_start = Column(
        DateTime, default=lambda: datetime.now(pytz.timezone("Asia/Kolkata"))
    )
    activation_end = Column(DateTime, nullable=True)


class PowerActivationRepo:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_table(self):
        Base.metadata.create_all(bind=self.engine)

    def drop_all_tables(self):
        Base.metadata.drop_all(bind=self.engine)

    def activate_power(self, stone_id: str, user_id: str) -> PowerActivation:
        session = self.SessionLocal()
        record = PowerActivation(
            stone_id=stone_id,
            user_id=user_id,
            status=PowerActivationStatus.ACTIVATED.value,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        session.expunge(record)
        session.close()
        return record

    def deactivate_power(self, record_id: int):
        session = self.SessionLocal()
        record = session.query(PowerActivation).filter_by(id=record_id).first()
        if record:
            record.activation_end = datetime.now(pytz.timezone("Asia/Kolkata"))
            record.status = PowerActivationStatus.DEACTIVATED.value
            session.commit()
            session.close()
        else:
            _logger.error(f"Record with id {record_id} not found")
