"""Test async_dispatcher.py"""

import asyncio
import json
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest
from oslash.either import Left, Right

from jsonrpcserver.async_dispatcher import (
    call,
    dispatch_deserialized,
    dispatch_request,
    dispatch_to_response_pure,
)
from jsonrpcserver.async_main import dispatch as async_dispatch
from jsonrpcserver.codes import (
    ERROR_INTERNAL_ERROR,
    ERROR_METHOD_NOT_FOUND,
    ERROR_SERVER_ERROR,
)
from jsonrpcserver.dispatcher import dispatch_to_response_pure as sync_dispatch_pure
from jsonrpcserver.exceptions import JsonRpcError
from jsonrpcserver.main import default_deserializer, default_validator, dispatch
from jsonrpcserver.request import Request
from jsonrpcserver.response import ErrorResponse, SuccessResponse, to_dict
from jsonrpcserver.result import ErrorResult, Result, Success, SuccessResult
from jsonrpcserver.sentinels import NOCONTEXT, NODATA
from jsonrpcserver.utils import identity

# pylint: disable=missing-function-docstring,duplicate-code


async def ping() -> Result:
    return Success("pong")


def sync_ping() -> Result:
    return Success("pong")


@pytest.mark.asyncio
async def test_call() -> None:
    assert await call(Request("ping", [], 1), NOCONTEXT, ping) == Right(
        SuccessResult("pong")
    )


@pytest.mark.asyncio
async def test_call_raising_jsonrpcerror() -> None:
    def method() -> None:
        raise JsonRpcError(code=1, message="foo", data=NODATA)

    assert await call(Request("ping", [], 1), NOCONTEXT, method) == Left(
        ErrorResult(1, "foo")
    )


@pytest.mark.asyncio
async def test_call_raising_exception() -> None:
    """The exception message must not reach the client by default."""

    def method() -> None:
        raise ValueError("foo")

    assert await call(Request("ping", [], 1), NOCONTEXT, method) == Left(
        ErrorResult(ERROR_INTERNAL_ERROR, "Internal error", NODATA)
    )


@pytest.mark.asyncio
async def test_call_raising_exception_debug() -> None:
    def method() -> None:
        raise ValueError("foo")

    assert await call(Request("ping", [], 1), NOCONTEXT, method, debug=True) == Left(
        ErrorResult(ERROR_INTERNAL_ERROR, "Internal error", "foo")
    )


@pytest.mark.asyncio
async def test_call_raising_exception_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def method() -> Result:
        raise ValueError("secret detail")

    await call(Request("ping", [], 1), NOCONTEXT, method)
    (record,) = caplog.records
    assert record.name == "jsonrpcserver.async_dispatcher"
    assert record.getMessage() == "Method 'ping' raised an exception"
    assert record.exc_info is not None
    assert str(record.exc_info[1]) == "secret detail"


@pytest.mark.asyncio
async def test_dispatch_request() -> None:
    request = Request("ping", [], 1)
    assert await dispatch_request({"ping": ping}, NOCONTEXT, request) == (
        request,
        Right(SuccessResult("pong")),
    )


@pytest.mark.asyncio
async def test_dispatch_request_method_not_found() -> None:
    request = Request("nope", [], 1)
    assert await dispatch_request({"ping": ping}, NOCONTEXT, request) == (
        request,
        Left(ErrorResult(ERROR_METHOD_NOT_FOUND, "Method not found", "nope")),
    )


@pytest.mark.asyncio
async def test_dispatch_deserialized() -> None:
    assert await dispatch_deserialized(
        {"ping": ping},
        NOCONTEXT,
        identity,
        {"jsonrpc": "2.0", "method": "ping", "id": 1},
    ) == Right(SuccessResponse("pong", 1))


@pytest.mark.asyncio
async def test_dispatch_to_response_pure_success() -> None:
    assert await dispatch_to_response_pure(
        deserializer=default_deserializer,
        validator=default_validator,
        post_process=identity,
        context=NOCONTEXT,
        methods={"ping": ping},
        request='{"jsonrpc": "2.0", "method": "ping", "id": 1}',
    ) == Right(SuccessResponse("pong", 1))


@pytest.mark.parametrize("debug,data", [(False, NODATA), (True, "foo")])
@patch("jsonrpcserver.async_dispatcher.dispatch_request", side_effect=ValueError("foo"))
@pytest.mark.asyncio
async def test_dispatch_to_response_pure_server_error(
    dispatch_request: Mock, debug: bool, data: Any
) -> None:
    async def hello() -> Result:
        return Success()

    methods = {"hello": hello}
    assert await dispatch_to_response_pure(
        deserializer=default_deserializer,
        validator=default_validator,
        post_process=identity,
        context=NOCONTEXT,
        methods=methods,
        request='{"jsonrpc": "2.0", "method": "hello", "id": 1}',
        debug=debug,
    ) == Left(ErrorResponse(ERROR_SERVER_ERROR, "Server error", data, None))
    dispatch_request.assert_called_once_with(
        methods, NOCONTEXT, Request("hello", [], 1), debug=debug
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize(
    "invalid",
    [
        1,
        None,
        "bad",
        {},
        {"jsonrpc": "2.0", "method": 1},
        [],
        [{"jsonrpc": "2.0", "method": "ping", "id": 99}],
    ],
)
async def test_batch_keeps_valid_members(asynchronous: bool, invalid: Any) -> None:
    called: List[int] = []

    def record(value: int) -> Result:
        called.append(value)
        return Success(value)

    async def async_record(value: int) -> Result:
        return record(value)

    request = json.dumps(
        [
            {"jsonrpc": "2.0", "method": "record", "params": [1], "id": "first"},
            invalid,
            {"jsonrpc": "2.0", "method": "record", "params": [2]},
            {"jsonrpc": "2.0", "method": "record", "params": [3], "id": None},
        ]
    )
    methods: Dict[str, Any] = {"record": async_record if asynchronous else record}
    response = (
        await async_dispatch(request, methods)
        if asynchronous
        else dispatch(request, methods)
    )
    assert called == [1, 2, 3]
    assert json.loads(response) == [
        {"jsonrpc": "2.0", "result": 1, "id": "first"},
        {
            "jsonrpc": "2.0",
            "error": {
                "code": -32600,
                "message": "Invalid request",
                "data": "The request failed schema validation",
            },
            "id": None,
        },
        {"jsonrpc": "2.0", "result": 3, "id": None},
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize(
    "payload,expected",
    [
        ("[1]", 1),
        ("[1, 2, 3]", 3),
        ("[]", 0),
        ("[", -1),
        ('[{"jsonrpc": "2.0", "method": "ping"}]', None),
    ],
)
async def test_batch_response_shape(
    asynchronous: bool, payload: str, expected: Any
) -> None:
    methods: Dict[str, Any] = {"ping": ping if asynchronous else sync_ping}
    response = (
        await async_dispatch(payload, methods)
        if asynchronous
        else dispatch(payload, methods)
    )
    if expected is None:
        assert response == ""
    elif expected > 0:
        errors = json.loads(response)
        assert len(errors) == expected
        assert all(error["error"]["code"] == -32600 for error in errors)
        assert all(error["id"] is None for error in errors)
    else:
        error = json.loads(response)
        assert error["error"]["code"] == (-32600 if expected == 0 else -32700)
        assert error["id"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("asynchronous", [False, True])
async def test_batch_custom_validator_and_context(asynchronous: bool) -> None:
    checked: List[Dict[str, Any]] = []

    def validator(member: Any) -> Any:
        checked.append(member)
        if member["id"] == 2:
            raise ValueError("rejected")
        return default_validator(member)

    def echo(context: str, value: str) -> Result:
        return Success(context + value)

    async def async_echo(context: str, value: str) -> Result:
        return echo(context, value)

    members = [
        {"jsonrpc": "2.0", "method": "echo", "params": ["data"], "id": n}
        for n in (1, 2, 3)
    ]
    methods: Dict[str, Any] = {"echo": async_echo if asynchronous else echo}
    response = (
        await async_dispatch(
            json.dumps(members), methods, validator=validator, context="prefix:"
        )
        if asynchronous
        else dispatch(
            json.dumps(members), methods, validator=validator, context="prefix:"
        )
    )
    assert checked == members
    results = json.loads(response)
    assert results[0]["result"] == results[2]["result"] == "prefix:data"
    assert results[1]["error"]["code"] == -32600
    assert results[1]["id"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("asynchronous", [False, True])
async def test_batch_post_process_preserves_none(asynchronous: bool) -> None:
    seen: List[Any] = []

    def post_process(response: Any) -> None:
        seen.append(to_dict(response))

    request = (
        '[1, {"jsonrpc": "2.0", "method": "ping", "id": 1}, '
        '{"jsonrpc": "2.0", "method": "ping"}]'
    )
    methods: Dict[str, Any] = {"ping": ping if asynchronous else sync_ping}
    options: Dict[str, Any] = {
        "deserializer": default_deserializer,
        "validator": default_validator,
        "methods": methods,
        "context": NOCONTEXT,
        "post_process": post_process,
        "request": request,
    }
    response = (
        await dispatch_to_response_pure(**options)
        if asynchronous
        else sync_dispatch_pure(**options)
    )
    assert response == [None, None]
    assert len(seen) == 2
    assert seen[0]["error"]["code"] == -32600
    assert seen[1] == {"jsonrpc": "2.0", "result": "pong", "id": 1}


@pytest.mark.asyncio
async def test_batch_async_members_run_concurrently() -> None:
    ready = asyncio.Event()
    started: List[int] = []

    async def rendezvous(value: int) -> Result:
        started.append(value)
        if len(started) == 2:
            ready.set()
        await ready.wait()
        return Success(value)

    request = json.dumps(
        [1]
        + [
            {"jsonrpc": "2.0", "method": "rendezvous", "params": [n], "id": n}
            for n in (1, 2)
        ]
    )
    response = await asyncio.wait_for(
        async_dispatch(request, {"rendezvous": rendezvous}), timeout=2
    )
    assert started == [1, 2]
    assert [member.get("result") for member in json.loads(response)] == [None, 1, 2]
