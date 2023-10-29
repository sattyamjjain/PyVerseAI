import socketio
from utils import get_logger

sio = socketio.Client()
_logger = get_logger(__name__)


@sio.event
def connect():
    _logger.info("Connection established")


@sio.event
def disconnect():
    _logger.info("Disconnected from server")


@sio.event
def activation_update(data):
    _logger.info("Activation Update:", data)


if __name__ == "__main__":
    sio.connect("http://localhost:5000")
    sio.wait()
