from time import sleep
from flask import Flask, request, jsonify
from celery import Celery
from config import BROKER_URL, CELERY_RESULT_BACKEND
from flask_socketio import SocketIO, join_room
from utils import get_logger
from db import PowerActivationRepo, PowerActivationStatus

_logger = get_logger(__name__)

app = Flask(__name__)

socketio = SocketIO(app, message_queue="redis://", logger=True)

celery = Celery(
    app.name,
    broker=BROKER_URL,
    broker_connection_retry_on_startup=True,
)
celery.conf.update(app.config)
celery.conf.result_backend = CELERY_RESULT_BACKEND


@app.route("/activate", methods=["POST"])
def activate():
    data = request.json
    stone_id = data.get("stone_id")
    user_id = data.get("user_id")
    power_duration = data.get("power_duration")

    activate_power.delay(stone_id, user_id, power_duration)

    return jsonify(
        {
            "status": "success",
            "message": "Power activation request received",
            "data": {
                "stone_id": stone_id,
                "user_id": user_id,
                "power_duration": power_duration,
            },
        }
    )


@celery.task
def activate_power(stone_id, user_id, power_duration):
    _logger.info(f"Activating power of stone {stone_id} for {power_duration} seconds.")
    power_activation_repo = PowerActivationRepo()
    record = power_activation_repo.activate_power(stone_id, user_id)
    socketio.emit(
        "activation_update",
        {
            "status": PowerActivationStatus.ACTIVATED.value,
            "user_id": user_id,
            "stone_id": stone_id,
        },
        namespace="/",
    )
    sleep(power_duration)
    power_activation_repo.deactivate_power(record.id)
    socketio.emit(
        "activation_update",
        {
            "status": PowerActivationStatus.DEACTIVATED.value,
            "user_id": user_id,
            "stone_id": stone_id,
        },
        namespace="/",
    )
    _logger.info(f"Power of stone {stone_id} has been deactivated.")


@socketio.on("connect")
def handle_connect():
    _logger.info("Client connected")


@socketio.on("disconnect")
def handle_disconnect():
    _logger.info("Client disconnected")


@socketio.on("join_room")
def handle_join_room(data):
    join_room(data["room"])


if __name__ == "__main__":
    socketio.run(app, port=5000, debug=True)
