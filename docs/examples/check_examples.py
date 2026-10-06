"""Start each example server in this directory and send it real requests.

Usage: python docs/examples/check_examples.py [EXAMPLE.py ...]

Each server must answer a "ping" request with "pong". The HTTP servers must
also answer a notification with 204 No Content and an empty body. The servers
that follow the Security page must refuse a batch over 100 requests and a body
over 1,000,000 bytes. The servers listen on localhost port 8000, as the docs
say. Needs the packages in requirements/examples.txt, and curl.

It also sends the quickstart server the curl command from the docs.
"""

import http.client
import json
import shlex
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

HERE = Path(__file__).parent
PORT = 8000
REQUEST = json.dumps({"jsonrpc": "2.0", "method": "ping", "id": 1})
NOTIFICATION = json.dumps({"jsonrpc": "2.0", "method": "ping"})
EXPECTED = {"jsonrpc": "2.0", "result": "pong", "id": 1}
BIG_BATCH = json.dumps(
    [{"jsonrpc": "2.0", "method": "ping", "id": n} for n in range(101)]
)
BATCH_REFUSED = {
    "jsonrpc": "2.0",
    "error": {
        "code": -32600,
        "message": "Invalid request",
        "data": "The batch has 101 requests. The limit is 100.",
    },
    "id": None,
}
MAX_BODY = 1_000_000

# The curl command in the README and on the home page. tests/test_docs.py
# checks that they show this command and this output.
CURL = (
    "curl -s -H 'Content-Type: application/json' "
    """-d '{"jsonrpc": "2.0", "method": "ping", "id": 1}' http://localhost:8000/"""
)
CURL_OUTPUT = '{"jsonrpc": "2.0", "result": "pong", "id": 1}'


def post(body: str) -> Tuple[int, str, str]:
    request = urllib.request.Request(
        f"http://localhost:{PORT}/",
        data=body.encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return (
                response.status,
                response.headers.get("Content-Type", ""),
                response.read().decode(),
            )
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), exc.read().decode()


def post_raw(body: Optional[bytes]) -> int:
    """POST without urllib's help: no Content-Length when body is None."""
    connection = http.client.HTTPConnection("localhost", PORT, timeout=10)
    try:
        if body is None:
            connection.putrequest("POST", "/")
            connection.putheader("Content-Type", "application/json")
            connection.endheaders()
        else:
            connection.request(
                "POST", "/", body=body, headers={"Content-Type": "application/json"}
            )
        return connection.getresponse().status
    finally:
        connection.close()


def post_raw_body(body: bytes) -> Tuple[int, str]:
    """POST bytes that may not be valid UTF-8. Return the status and body."""
    connection = http.client.HTTPConnection("localhost", PORT, timeout=10)
    try:
        connection.request("POST", "/", body=body)
        response = connection.getresponse()
        return response.status, response.read().decode()
    finally:
        connection.close()


def check_ping_and_notification() -> None:
    status, content_type, body = post(REQUEST)
    assert status == 200, status
    assert content_type.startswith("application/json"), content_type
    assert json.loads(body) == EXPECTED, body
    status, _, body = post(NOTIFICATION)
    assert (status, body) == (204, ""), (status, body)


def check_limits(too_large: int) -> None:
    status, _, body = post(BIG_BATCH)
    assert status == 200, status
    assert json.loads(body) == BATCH_REFUSED, body
    status = post_raw(b" " * (MAX_BODY + 1))
    assert status == too_large, status


def check_quickstart() -> None:
    check_ping_and_notification()
    output = subprocess.run(
        shlex.split(CURL), capture_output=True, text=True, timeout=30, check=True
    ).stdout
    assert output == CURL_OUTPUT, output


def check_http_server() -> None:
    check_ping_and_notification()
    check_limits(413)
    assert post_raw(None) == 411
    status, body = post_raw_body(b'{"jsonrpc": "2.0", "method": "\xff", "id": 1}')
    assert status == 200, status
    assert json.loads(body)["error"]["code"] == -32700, body


def check_http(too_large: int) -> Callable[[], None]:
    def check() -> None:
        check_ping_and_notification()
        check_limits(too_large)

    return check


def check_websockets() -> None:
    from websockets.sync.client import connect

    with connect(f"ws://localhost:{PORT}", max_size=None) as websocket:
        websocket.send(REQUEST)
        assert json.loads(websocket.recv(timeout=10)) == EXPECTED
        websocket.send(BIG_BATCH)
        assert json.loads(websocket.recv(timeout=10)) == BATCH_REFUSED


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
        client.send_string(BIG_BATCH)
        assert json.loads(client.recv_string()) == BATCH_REFUSED
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
        client.emit("message", BIG_BATCH)
        event, data = client.receive(timeout=10)
        assert json.loads(data) == BATCH_REFUSED, data


EXAMPLES: Dict[str, Callable[[], None]] = {
    "quickstart.py": check_quickstart,
    "http_server.py": check_http_server,
    "flask_server.py": check_http(413),
    "werkzeug_server.py": check_http(413),
    # Django answers a body over DATA_UPLOAD_MAX_MEMORY_SIZE with 400.
    "django_server.py": check_http(400),
    "fastapi_server.py": check_http(413),
    "aiohttp_server.py": check_http(413),
    "sanic_server.py": check_http(413),
    "tornado_server.py": check_http(400),
    "websockets_server.py": check_websockets,
    "zeromq_server.py": check_zeromq,
    "zeromq_async_server.py": check_zeromq,
    "socketio_server.py": check_socketio,
}
# Files that aren't servers.
NOT_SERVERS = {"check_examples.py"}


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
    on_disk = {path.name for path in HERE.glob("*.py")} - NOT_SERVERS
    missing = on_disk - set(EXAMPLES)
    if missing:
        print(f"Examples with no check: {sorted(missing)}")
        return 1
    results = [run(name) for name in names or EXAMPLES]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
