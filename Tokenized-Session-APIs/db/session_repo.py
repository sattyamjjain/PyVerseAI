from typing import Optional, List
from datetime import datetime
from mongoengine import (
    Document,
    StringField,
    DateTimeField,
    DoesNotExist,
    connect,
    BooleanField,
    IntField,
)
from config import MONGO_CONNECTION_STRING
from utils import IST


class Session(Document):
    _id: int = IntField(min_value=1, required=True, primary_key=True)
    student_name: str = StringField(max_length=16)
    dean_name: str = StringField(max_length=16, required=True)
    is_booked: bool = BooleanField(default=False)
    is_paid: bool = BooleanField(default=False)
    start_time = DateTimeField()
    end_time = DateTimeField()
    updated_at = DateTimeField(default=datetime.now(tz=IST))

    @property
    def id(self):
        return self._id


class SessionRepo:
    __connected = False

    def __init__(self):
        if not SessionRepo.__connected:
            self._instantiate_db_connection()

    @classmethod
    def _instantiate_db_connection(cls):
        if not cls.__connected:
            connect(host=MONGO_CONNECTION_STRING)
            cls.__connected = True

    @staticmethod
    def get_by_id(_id: int) -> Optional[Session]:
        try:
            return Session.objects.get(_id=_id)
        except DoesNotExist as e:
            return None

    @staticmethod
    def get(
        is_paid: bool = False,
        dean_name: str = None,
        student_name: str = None,
    ) -> Optional[List[Session]]:
        try:
            _query = {}
            if is_paid:
                _query["is_paid"] = is_paid
            if dean_name:
                _query["dean_name"] = dean_name
            if student_name:
                _query["student_name"] = student_name
            return Session.objects(__raw__=_query)
        except DoesNotExist as e:
            return None

    @staticmethod
    def add_session(dean_name: str, is_paid: bool = False) -> Session:
        return Session(
            _id=Session.objects.count() + 1,
            dean_name=dean_name,
            is_booked=False,
            is_paid=is_paid,
        ).save()

    @staticmethod
    def edit_session(_id: int, st_name: str, start_time: datetime, end_time: datetime):
        s = Session.objects.get(_id=_id)
        s.student_name = st_name
        s.start_time = start_time
        s.end_time = end_time
        s.is_booked = True
        s.updated_at = datetime.now(tz=IST)
        s.save()
