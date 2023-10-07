from functools import wraps
from flask import request
from db.auth_repo import AuthRepo


def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        if not token:
            return {
                "message": "Authentication token is missing",
                "statusCode": 401,
            }
        try:
            auth = AuthRepo().get_auth_by_token(token)
            if auth is None:
                return {
                    "message": "Invalid Authentication token!",
                    "statusCode": 401,
                }
        except Exception as e:
            return {
                "message": str(e),
                "statusCode": 500,
            }
        return f(auth, *args, **kwargs)

    return decorator
