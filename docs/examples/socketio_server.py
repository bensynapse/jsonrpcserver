from flask import Flask
from flask_socketio import SocketIO, send

from jsonrpcserver import Result, Success, dispatch, method

app = Flask(__name__)
socketio = SocketIO(app)


@method
def ping() -> Result:
    return Success("pong")


@socketio.on("message")
def handle_message(message: str) -> None:
    if response := dispatch(message):
        send(response)


if __name__ == "__main__":
    # Werkzeug's server is for development. See the Flask-SocketIO docs for
    # production servers.
    socketio.run(app, host="localhost", port=5000, allow_unsafe_werkzeug=True)
