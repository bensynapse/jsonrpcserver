"""Test async_main.py"""

import json

import pytest
from oslash.either import Right

from jsonrpcserver.async_main import (
    dispatch_to_json,
    dispatch_to_response,
    dispatch_to_serializable,
)
from jsonrpcserver.response import SuccessResponse
from jsonrpcserver.result import Result, Success

# pylint: disable=missing-function-docstring


async def ping() -> Result:
    return Success("pong")


@pytest.mark.asyncio
async def test_dispatch_to_response() -> None:
    assert await dispatch_to_response(
        '{"jsonrpc": "2.0", "method": "ping", "id": 1}', {"ping": ping}
    ) == Right(SuccessResponse("pong", 1))


@pytest.mark.asyncio
async def test_dispatch_to_serializable() -> None:
    assert await dispatch_to_serializable(
        '{"jsonrpc": "2.0", "method": "ping", "id": 1}', {"ping": ping}
    ) == {"jsonrpc": "2.0", "result": "pong", "id": 1}


@pytest.mark.asyncio
async def test_dispatch_to_json() -> None:
    assert (
        await dispatch_to_json(
            '{"jsonrpc": "2.0", "method": "ping", "id": 1}', {"ping": ping}
        )
        == '{"jsonrpc": "2.0", "result": "pong", "id": 1}'
    )


@pytest.mark.asyncio
async def test_dispatch_to_json_notification() -> None:
    assert (
        await dispatch_to_json('{"jsonrpc": "2.0", "method": "ping"}', {"ping": ping})
        == ""
    )


SECRET = "could not connect: postgresql://admin:hunter2@db.internal/prod"


async def leak() -> Result:
    raise RuntimeError(SECRET)


@pytest.mark.asyncio
async def test_dispatch_hides_exception_message() -> None:
    response = await dispatch_to_json(
        '{"jsonrpc": "2.0", "method": "leak", "id": 1}', {"leak": leak}
    )
    assert json.loads(response) == {
        "jsonrpc": "2.0",
        "error": {"code": -32603, "message": "Internal error"},
        "id": 1,
    }
    assert "hunter2" not in response


@pytest.mark.asyncio
async def test_dispatch_debug_shows_exception_message() -> None:
    response = await dispatch_to_json(
        '{"jsonrpc": "2.0", "method": "leak", "id": 1}', {"leak": leak}, debug=True
    )
    assert json.loads(response) == {
        "jsonrpc": "2.0",
        "error": {"code": -32603, "message": "Internal error", "data": SECRET},
        "id": 1,
    }


@pytest.mark.asyncio
async def test_dispatch_batch_hides_exception_message() -> None:
    response = await dispatch_to_json(
        '[{"jsonrpc": "2.0", "method": "leak", "id": 1},'
        ' {"jsonrpc": "2.0", "method": "ping", "id": 2}]',
        {"leak": leak, "ping": ping},
    )
    assert json.loads(response) == [
        {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": "Internal error"},
            "id": 1,
        },
        {"jsonrpc": "2.0", "result": "pong", "id": 2},
    ]
