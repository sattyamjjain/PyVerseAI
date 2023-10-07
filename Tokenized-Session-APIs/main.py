from flask import request, Flask
from service import register, login, list_session, book_slot, create_slot
from utils import catch_exp
from auth import token_required

app = Flask(__name__)


@app.route("/register", methods=["POST"])
@catch_exp()
def handle_student_registration():
    req_json = request.json
    register(
        req_json["name"],
        req_json["university_id"],
        req_json["password"],
        req_json.get("role", "STUDENT"),
    )
    return {"statusCode": 200, "body": {"message": "Successfully registered"}}


@app.route("/login", methods=["POST"])
@catch_exp()
def handle_student_login():
    req_json = request.json
    token = login(req_json["university_id"], req_json["password"])
    return {"statusCode": 200, "body": {"token": token}}


@app.route("/sessions", methods=["GET"])
@token_required
@catch_exp()
def handle_list_sessions(auth):
    return {"statusCode": 200, "body": {"sessions": list_session(auth)}}


@app.route("/session", methods=["POST"])
@token_required
@catch_exp()
def handle_create_session(auth):
    req_json = request.json
    create_slot(req_json["dean_name"], req_json.get("is_paid", False))
    return {"statusCode": 200, "body": {"message": "Session created successfully"}}


@app.route("/slot", methods=["PUT"])
@token_required
@catch_exp()
def handle_book_slot(auth):
    req_json = request.json
    book_slot(
        req_json["id"],
        req_json["student_name"],
        req_json["start_time"],
        req_json.get("end_time"),
    )
    return {"statusCode": 200, "body": {"message": "Slot booked successfully"}}


if __name__ == "__main__":
    app.run(debug=True)
