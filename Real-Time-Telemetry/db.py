from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import pytz
from config import DATABASE_URL

Base = declarative_base()


class MeterValue(Base):
    __tablename__ = "meter_values"

    id = Column(Integer, primary_key=True, autoincrement=True)
    charge_point_id = Column(String, nullable=False)
    payload = Column(Text, nullable=False)
    updated_at = Column(
        DateTime, default=lambda: datetime.now(pytz.timezone("Asia/Kolkata"))
    )


class MeterValueRepo:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_table(self):
        Base.metadata.create_all(bind=self.engine)

    def add_value(self, charge_point_id: str, meter_value: str):
        session = self.SessionLocal()
        record = MeterValue(charge_point_id=charge_point_id, payload=meter_value)
        session.add(record)
        session.commit()
        session.close()

    def get_value(self, record_id: str):
        session = self.SessionLocal()
        record = session.query(MeterValue).filter_by(id=record_id).first()
        session.close()
        return record

    def get_values(self, charge_point_ids: str, page: int, per_page: int):
        session = self.SessionLocal()
        query = session.query(MeterValue)

        if charge_point_ids:
            charge_point_ids = charge_point_ids.split(",")
            query = query.filter(MeterValue.charge_point_id.in_(charge_point_ids))

        records = query.offset((page - 1) * per_page).limit(per_page).all()
        session.close()
        return records
