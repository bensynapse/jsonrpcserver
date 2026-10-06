"""Test server.py"""

import http.client
import json
import logging
import sys
import threading
from typing import Dict, Iterator, Optional, Tuple
from unittest.mock import Mock, patch

import pytest

from jsonrpcserver import Result, Success, method
from jsonrpcserver.server import RequestHandler, ThreadingHTTPServer, serve


@patch("jsonrpcserver.server.ThreadingHTTPServer")
def test_serve(server: Mock) -> None:
    serve()
    server.assert_called_once_with(("", 5000), RequestHandler)
    server.return_value.serve_forever.assert_called_once_with()
    server.return_value.server_close.assert_called_once_with()


@patch("jsonrpcserver.server.ThreadingHTTPServer")
def test_serve_name_and_port(server: Mock) -> None:
    serve("localhost", 8080)
    server.assert_called_once_with(("localhost", 8080), RequestHandler)


@patch("jsonrpcserver.server.ThreadingHTTPServer")
def test_serve_closes_on_interrupt(server: Mock) -> None:
    server.return_value.serve_forever.side_effect = KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        serve()
    server.return_value.server_close.assert_called_once_with()


@method(name="server_test_ping")
def ping() -> Result:
    return Success("pong")


@pytest.fixture
def port() -> Iterator[int]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), RequestHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()


def post(
    port: int, body: Optional[bytes], headers: Optional[Dict[str, str]] = None
) -> Tuple[int, bytes, Optional[str]]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        if body is None:
            # No body and no Content-Length header.
            connection.putrequest("POST", "/")
            connection.endheaders()
        else:
            connection.request("POST", "/", body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, response.read(), response.getheader("Content-Type")
    finally:
        connection.close()


PING = b'{"jsonrpc": "2.0", "method": "server_test_ping", "id": 1}'


def test_request(port: int) -> None:
    assert post(port, PING) == (
        200,
        b'{"jsonrpc": "2.0", "result": "pong", "id": 1}',
        "application/json",
    )


def test_notification(port: int) -> None:
    status, body, _ = post(port, b'{"jsonrpc": "2.0", "method": "server_test_ping"}')
    assert (status, body) == (204, b"")


def test_invalid_utf8(port: int) -> None:
    status, body, _ = post(port, b"\xff\xfe")
    assert status == 200
    response = json.loads(body)
    assert response["error"]["code"] == -32700
    assert response["id"] is None


def test_no_content_length(port: int) -> None:
    assert post(port, None)[0] == 411


@pytest.mark.parametrize("length", ["abc", "-1"])
def test_bad_content_length(port: int, length: str) -> None:
    assert post(port, b"", {"Content-Length": length})[0] == 400


def test_no_stderr(port: int, monkeypatch: pytest.MonkeyPatch) -> None:
    """PyInstaller apps built with --noconsole have no stderr (#269)."""
    monkeypatch.setattr(sys, "stderr", None)
    assert post(port, PING)[0] == 200


def test_requests_are_logged(port: int, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="jsonrpcserver.server"):
        post(port, PING)
    assert any('"POST / HTTP/1.1" 200' in r.getMessage() for r in caplog.records)
