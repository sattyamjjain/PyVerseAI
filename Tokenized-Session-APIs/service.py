import uuid
import datetime
from typing import List, Optional

from db.auth_repo import AuthRepo, Auth
from db.session_repo import SessionRepo
from utils import convert_to_hash, get_datetime_from_millis, IST


def __is_session_available(start_time: Optional[datetime.datetime]) -> bool:
    if start_time is None:
        return True
    return start_time >= datetime.datetime.now(tz=IST)


def register(name: str, uni_id: str, pwd: str, role: str):
    if role not in ["STUDENT", "DEAN"]:
        raise AssertionError("Not a valid role")
    _ar = AuthRepo()
    _pwd_hash = convert_to_hash(pwd)
    _auth = _ar.get_auth_by_id(_pwd_hash)
    if _auth:
        raise AssertionError(f"{_auth.name} already registered")
    _ar.add_auth(_pwd_hash, name, uni_id, pwd, str(uuid.uuid4()), role)


def login(uni_id: str, pwd: str) -> str:
    s = AuthRepo().get_auth_by_uni_id_and_password(uni_id, pwd)
    if s is None:
        raise AssertionError("UnRegistered")
    return s.to_mongo().to_dict()["token"]


def list_session(auth: Auth) -> List[dict]:
    _sr = SessionRepo()

    sessions = []
    for sess in _sr.get() if auth.role == "STUDENT" else _sr.get(dean_name=auth.name):
        sess_as_dict = sess.to_mongo().to_dict()
        if sess_as_dict.get("start_time"):
            sess_as_dict["start_time"] = sess_as_dict["start_time"].astimezone(IST)
        if sess_as_dict.get("end_time"):
            sess_as_dict["end_time"] = sess_as_dict["end_time"].astimezone(IST)
        if not sess_as_dict["is_booked"] and __is_session_available(
            sess_as_dict.get("start_time")
        ):
            sessions.append(sess_as_dict)
    return sessions


def create_slot(dean_name: str, is_paid: bool = False):
    SessionRepo().add_session(dean_name, is_paid)


def book_slot(_id: int, st_name: str, start_time: int, end_time: int = None):
    start_time = get_datetime_from_millis(start_time)
    if (
        start_time.strftime("%A") not in ["Thursday", "Friday"]
        or start_time.hour != 10
        or start_time.minute != 0
        or start_time.second != 0
    ):
        raise AssertionError(f"Not applicable slots for {start_time}")
    if end_time:
        end_time = get_datetime_from_millis(end_time)
        if end_time < start_time or end_time - start_time != datetime.timedelta(
            hours=1
        ):
            raise AssertionError("End time should be in difference of max 1 hour")
    else:
        end_time = start_time + datetime.timedelta(hours=1)
    if start_time < datetime.datetime.now(tz=IST) or end_time < datetime.datetime.now(
        tz=IST
    ):
        raise AssertionError("Not allowed to book for past time")
    _sr = SessionRepo()
    _slot = _sr.get_by_id(_id=_id)
    if _slot is None:
        raise AssertionError(f"Not a valid session id {_id}")
    if _slot.is_booked:
        if _slot.student_name == st_name:
            raise AssertionError(f"Already exists a booked slot")
        _id = _sr.add_session(_slot.dean_name, _slot.is_paid).id
    _sr.edit_session(_id, st_name, start_time, end_time)
