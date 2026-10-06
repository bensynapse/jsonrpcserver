from flask import Flask
from flask_socketio import SocketIO, send

from jsonrpcserver import Result, Success, dispatch, method

app = Flask(__name__)
# A bigger message is rejected. 1,000,000 bytes is also the default.
socketio = SocketIO(app, max_http_buffer_size=1_000_000)


@method
def ping() -> Result:
    return Success("pong")


@socketio.on("message")
def handle_message(message: str) -> None:
    # max_batch_size: see the Security page.
    if response := dispatch(message, max_batch_size=100):
        send(response)


if __name__ == "__main__":
    # Werkzeug's server is for development. See the Flask-SocketIO docs for
    # production servers.
    socketio.run(app, host="localhost", port=8000, allow_unsafe_werkzeug=True)
