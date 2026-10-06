"""Test main.py"""

import json

from oslash.either import Right  # type: ignore

from jsonrpcserver.main import (
    dispatch_to_json,
    dispatch_to_response,
    dispatch_to_serializable,
)
from jsonrpcserver.response import SuccessResponse
from jsonrpcserver.result import Result, Success

# pylint: disable=missing-function-docstring


def ping() -> Result:
    return Success("pong")


def test_dispatch_to_response() -> None:
    assert dispatch_to_response(
        '{"jsonrpc": "2.0", "method": "ping", "id": 1}', {"ping": ping}
    ) == Right(SuccessResponse("pong", 1))


def test_dispatch_to_serializable() -> None:
    assert dispatch_to_serializable(
        '{"jsonrpc": "2.0", "method": "ping", "id": 1}', {"ping": ping}
    ) == {"jsonrpc": "2.0", "result": "pong", "id": 1}


def test_dispatch_to_json() -> None:
    assert (
        dispatch_to_json(
            '{"jsonrpc": "2.0", "method": "ping", "id": 1}', {"ping": ping}
        )
        == '{"jsonrpc": "2.0", "result": "pong", "id": 1}'
    )


def test_dispatch_to_json_notification() -> None:
    assert (
        dispatch_to_json('{"jsonrpc": "2.0", "method": "ping"}', {"ping": ping}) == ""
    )


SECRET = "could not connect: postgresql://admin:hunter2@db.internal/prod"


def leak() -> Result:
    raise RuntimeError(SECRET)


def test_dispatch_hides_exception_message() -> None:
    response = dispatch_to_json(
        '{"jsonrpc": "2.0", "method": "leak", "id": 1}', {"leak": leak}
    )
    assert json.loads(response) == {
        "jsonrpc": "2.0",
        "error": {"code": -32603, "message": "Internal error"},
        "id": 1,
    }
    assert "hunter2" not in response


def test_dispatch_debug_shows_exception_message() -> None:
    assert json.loads(
        dispatch_to_json(
            '{"jsonrpc": "2.0", "method": "leak", "id": 1}', {"leak": leak}, debug=True
        )
    ) == {
        "jsonrpc": "2.0",
        "error": {"code": -32603, "message": "Internal error", "data": SECRET},
        "id": 1,
    }


def test_dispatch_to_serializable_debug() -> None:
    assert dispatch_to_serializable(
        '{"jsonrpc": "2.0", "method": "leak", "id": 1}', {"leak": leak}, debug=True
    ) == {
        "jsonrpc": "2.0",
        "error": {"code": -32603, "message": "Internal error", "data": SECRET},
        "id": 1,
    }
