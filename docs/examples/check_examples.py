"""Start each example server in this directory and send it real requests.

Usage: python docs/examples/check_examples.py [EXAMPLE.py ...]

Each server must answer a "ping" request with "pong". The HTTP servers must
also answer a notification with 204 No Content and an empty body. The servers
listen on localhost port 5000, as the docs say. Needs the packages in
requirements/examples.txt.
"""

import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Tuple

HERE = Path(__file__).parent
PORT = 5000
REQUEST = json.dumps({"jsonrpc": "2.0", "method": "ping", "id": 1})
NOTIFICATION = json.dumps({"jsonrpc": "2.0", "method": "ping"})
EXPECTED = {"jsonrpc": "2.0", "result": "pong", "id": 1}


def post(body: str) -> Tuple[int, str, str]:
    request = urllib.request.Request(
        f"http://localhost:{PORT}/",
        data=body.encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return (
            response.status,
            response.headers.get("Content-Type", ""),
            response.read().decode(),
        )


def check_http() -> None:
    status, content_type, body = post(REQUEST)
    assert status == 200, status
    assert content_type.startswith("application/json"), content_type
    assert json.loads(body) == EXPECTED, body
    status, _, body = post(NOTIFICATION)
    assert (status, body) == (204, ""), (status, body)


def check_websockets() -> None:
    from websockets.sync.client import connect

    with connect(f"ws://localhost:{PORT}") as websocket:
        websocket.send(REQUEST)
        assert json.loads(websocket.recv(timeout=10)) == EXPECTED


def check_zeromq() -> None:
    import zmq

    context = zmq.Context()
    client = context.socket(zmq.REQ)
    client.setsockopt(zmq.RCVTIMEO, 10000)
    client.setsockopt(zmq.LINGER, 0)
    client.connect(f"tcp://localhost:{PORT}")
    try:
        client.send_string(REQUEST)
        assert json.loads(client.recv_string()) == EXPECTED
        client.send_string(NOTIFICATION)
        assert client.recv_string() == ""
    finally:
        client.close()
        context.term()


def check_socketio() -> None:
    import socketio

    with socketio.SimpleClient() as client:
        client.connect(f"http://localhost:{PORT}")
        client.emit("message", REQUEST)
        event, data = client.receive(timeout=10)
        assert event == "message", event
        assert json.loads(data) == EXPECTED, data


EXAMPLES: Dict[str, Callable[[], None]] = {
    "http_server.py": check_http,
    "serve.py": check_http,
    "flask_server.py": check_http,
    "werkzeug_server.py": check_http,
    "django_server.py": check_http,
    "fastapi_server.py": check_http,
    "aiohttp_server.py": check_http,
    "sanic_server.py": check_http,
    "tornado_server.py": check_http,
    "websockets_server.py": check_websockets,
    "zeromq_server.py": check_zeromq,
    "zeromq_async_server.py": check_zeromq,
    "socketio_server.py": check_socketio,
}


def port_open() -> bool:
    try:
        with socket.create_connection(("localhost", PORT), timeout=1):
            return True
    except OSError:
        return False


def run(example: str) -> bool:
    if port_open():
        print(f"FAIL {example}: port {PORT} is already in use")
        return False
    server = subprocess.Popen(
        [sys.executable, str(HERE / example)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + 60
        while not port_open():
            if server.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError("the server didn't start")
            time.sleep(0.2)
        EXAMPLES[example]()
    except Exception as exc:
        server.kill()
        output, _ = server.communicate()
        print(f"FAIL {example}: {type(exc).__name__}: {exc}\n{output}")
        return False
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.communicate()
    # Wait for the port to be free for the next example.
    deadline = time.monotonic() + 10
    while port_open() and time.monotonic() < deadline:
        time.sleep(0.2)
    print(f"ok   {example}")
    return True


def main(names: List[str]) -> int:
    on_disk = {path.name for path in HERE.glob("*.py")} - {Path(__file__).name}
    missing = on_disk - set(EXAMPLES)
    if missing:
        print(f"Examples with no check: {sorted(missing)}")
        return 1
    results = [run(name) for name in names or EXAMPLES]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
