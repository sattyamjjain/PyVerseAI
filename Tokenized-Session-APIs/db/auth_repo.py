from typing import Optional

import pytz
from datetime import datetime
from mongoengine import Document, StringField, DateTimeField, DoesNotExist, connect
from config import MONGO_CONNECTION_STRING


class Auth(Document):
    _id: str = StringField(required=True, primary_key=True)
    name: str = StringField(required=True, max_length=16)
    university_id: str = StringField(required=True)
    password: str = StringField(required=True)
    token: str = StringField(required=True)
    role: str = StringField()
    registered_at = DateTimeField(default=datetime.now(tz=pytz.timezone("Asia/Kolkata")))


class AuthRepo:
    __connected = False

    def __init__(self):
        if not AuthRepo.__connected:
            self._instantiate_db_connection()

    @classmethod
    def _instantiate_db_connection(cls):
        if not cls.__connected:
            connect(host=MONGO_CONNECTION_STRING)
            cls.__connected = True

    @staticmethod
    def get_auth_by_id(_id: str) -> Optional[Auth]:
        try:
            return Auth.objects.get(_id=_id)
        except DoesNotExist:
            return None

    @staticmethod
    def get_auth_by_uni_id_and_password(uni_id: str, pwd: str) -> Optional[Auth]:
        try:
            return Auth.objects.get(university_id=uni_id, password=pwd)
        except DoesNotExist:
            return None

    @staticmethod
    def get_auth_by_token(token: str) -> Optional[Auth]:
        try:
            return Auth.objects.get(token=token)
        except DoesNotExist:
            return None

    @staticmethod
    def add_auth(_id: str, name: str, uni_id: str, pwd: str, token: str, role: str):
        Auth(
            _id=_id,
            name=name,
            university_id=uni_id,
            password=pwd,
            token=token,
            role=role
        ).save()
