"""dispatch must always give a valid JSON-RPC response, whatever the request and
whatever the methods do. These tests cover the ways it used to raise or collapse a
whole batch into one error.
"""

import datetime
import json
import subprocess
import sys
from typing import Any, Dict
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from oslash.either import Right  # type: ignore

from jsonrpcserver import Result, Success, async_dispatch, dispatch
from jsonrpcserver.dispatcher import NORESPONSE, dispatch_member, member_id
from jsonrpcserver.main import default_validator
from jsonrpcserver.response import SuccessResponse
from jsonrpcserver.sentinels import NOCONTEXT
from jsonrpcserver.utils import identity

INTERNAL_ERROR = {"code": -32603, "message": "Internal error"}


def ping() -> Result:
    return Success("pong")


async def aping() -> Result:
    return Success("pong")


def now() -> Result:
    return Success(datetime.datetime(2026, 1, 1))


async def anow() -> Result:
    return Success(datetime.date(2026, 1, 1))


def nan() -> Result:
    return Success(float("nan"))


def returns_none() -> None:
    return None


METHODS: Dict[str, Any] = {
    "ping": ping,
    "now": now,
    "nan": nan,
    "none": returns_none,
    "max": max,
}


def request(method: str, id_: Any = 1) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "method": method, "id": id_}


# Results that can't be serialized


def test_unserializable_result() -> None:
    assert json.loads(dispatch(json.dumps(request("now")), METHODS)) == {
        "jsonrpc": "2.0",
        "error": INTERNAL_ERROR,
        "id": 1,
    }


def test_unserializable_result_debug() -> None:
    response = json.loads(dispatch(json.dumps(request("now")), METHODS, debug=True))
    assert response["error"]["data"] == (
        "Object of type datetime is not JSON serializable"
    )


def test_unserializable_result_in_batch_keeps_other_responses() -> None:
    batch = [request("now", 1), request("ping", 2)]
    assert json.loads(dispatch(json.dumps(batch), METHODS)) == [
        {"jsonrpc": "2.0", "error": INTERNAL_ERROR, "id": 1},
        {"jsonrpc": "2.0", "result": "pong", "id": 2},
    ]


def test_unserializable_result_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    dispatch(json.dumps(request("now")), METHODS)
    assert any(
        record.getMessage() == "Could not serialize the response for request id 1"
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_unserializable_result_async() -> None:
    batch = [request("anow", 1), request("aping", 2)]
    response = await async_dispatch(json.dumps(batch), {"anow": anow, "aping": aping})
    assert json.loads(response) == [
        {"jsonrpc": "2.0", "error": INTERNAL_ERROR, "id": 1},
        {"jsonrpc": "2.0", "result": "pong", "id": 2},
    ]


def test_custom_serializer_is_still_used() -> None:
    def serializer(obj: Any) -> str:
        return json.dumps(obj, default=str)

    assert json.loads(
        dispatch(json.dumps(request("now")), METHODS, serializer=serializer)
    ) == {"jsonrpc": "2.0", "result": "2026-01-01 00:00:00", "id": 1}


# NaN and Infinity are not JSON


def test_nan_result_is_an_error() -> None:
    response = dispatch(json.dumps(request("nan")), METHODS)
    assert json.loads(response) == {"jsonrpc": "2.0", "error": INTERNAL_ERROR, "id": 1}


def test_nan_allowed_with_plain_json_dumps() -> None:
    """Passing json.dumps restores the old output, for anyone who relies on it."""
    response = dispatch(json.dumps(request("nan")), METHODS, serializer=json.dumps)
    assert response == '{"jsonrpc": "2.0", "result": NaN, "id": 1}'


def test_infinite_id_gets_null_id() -> None:
    response = dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1e400}', METHODS)
    assert json.loads(response) == {
        "jsonrpc": "2.0",
        "error": INTERNAL_ERROR,
        "id": None,
    }


def test_serializer_that_always_fails() -> None:
    def serializer(obj: Any) -> str:
        raise RuntimeError("broken")

    response = dispatch(json.dumps(request("ping")), METHODS, serializer=serializer)
    assert json.loads(response) == {
        "jsonrpc": "2.0",
        "error": INTERNAL_ERROR,
        "id": None,
    }


# One bad batch member must not take the others down


def test_builtin_without_signature() -> None:
    """max has no signature inspect can read. It used to collapse the batch."""
    batch = [{**request("max", 1), "params": [1, 2]}, request("ping", 2)]
    assert json.loads(dispatch(json.dumps(batch), METHODS)) == [
        {"jsonrpc": "2.0", "error": INTERNAL_ERROR, "id": 1},
        {"jsonrpc": "2.0", "result": "pong", "id": 2},
    ]


def test_method_without_signature_is_called() -> None:
    """If inspect can't read the signature, the method is called anyway."""

    def wrap(value: Any) -> Result:
        return Success(value)

    with patch("jsonrpcserver.dispatcher.signature", side_effect=ValueError("none")):
        response = dispatch(
            '{"jsonrpc": "2.0", "method": "wrap", "params": [5], "id": 1}',
            {"wrap": wrap},
        )
    assert json.loads(response) == {"jsonrpc": "2.0", "result": 5, "id": 1}


def test_non_dict_member_without_validator() -> None:
    response = dispatch(
        json.dumps([1, request("ping", 2)]), METHODS, validator=lambda _: None
    )
    assert json.loads(response) == [
        {
            "jsonrpc": "2.0",
            "error": {"code": -32000, "message": "Server error"},
            "id": None,
        },
        {"jsonrpc": "2.0", "result": "pong", "id": 2},
    ]


def test_failing_post_process_reaches_the_outer_handler() -> None:
    def post_process(response: Any) -> Any:
        if response._value.result == "boom":
            raise RuntimeError("post_process failed")
        return response

    def boom() -> Result:
        return Success("boom")

    with pytest.raises(RuntimeError):
        # The error response goes through post_process too, and raises again. That
        # failure isn't hidden.
        dispatch_member(
            default_validator, {"boom": boom}, NOCONTEXT, post_process, request("boom")
        )
    assert dispatch_member(
        default_validator, {"ping": ping}, NOCONTEXT, post_process, request("ping", 7)
    ) == Right(SuccessResponse("pong", 7))


def test_dispatch_member_notification() -> None:
    assert (
        dispatch_member(
            default_validator,
            METHODS,
            NOCONTEXT,
            identity,
            {"jsonrpc": "2.0", "method": "ping"},
        )
        is NORESPONSE
    )


@pytest.mark.parametrize(
    "member,expected",
    [
        ({"id": 5}, 5),
        ({"id": "x"}, "x"),
        ({"id": None}, None),
        ({"id": [1]}, None),
        ({}, None),
        (1, None),
    ],
)
def test_member_id(member: Any, expected: Any) -> None:
    assert member_id(member) == expected


@pytest.mark.asyncio
async def test_non_dict_member_without_validator_async() -> None:
    response = await async_dispatch(
        json.dumps([1, request("aping", 2)]), {"aping": aping}, validator=lambda _: None
    )
    assert json.loads(response) == [
        {
            "jsonrpc": "2.0",
            "error": {"code": -32000, "message": "Server error"},
            "id": None,
        },
        {"jsonrpc": "2.0", "result": "pong", "id": 2},
    ]


# Mixing sync and async methods


@pytest.mark.asyncio
async def test_sync_method_with_async_dispatch() -> None:
    response = await async_dispatch(json.dumps(request("ping")), {"ping": ping})
    assert json.loads(response) == {"jsonrpc": "2.0", "result": "pong", "id": 1}


def test_async_method_with_sync_dispatch(recwarn: pytest.WarningsRecorder) -> None:
    response = dispatch(json.dumps(request("aping")), {"aping": aping}, debug=True)
    assert json.loads(response)["error"] == {
        **INTERNAL_ERROR,
        "data": "Method 'aping' is async. Use async_dispatch to call async methods.",
    }
    # The coroutine is closed, so there's no "never awaited" warning.
    assert not [w for w in recwarn if issubclass(w.category, RuntimeWarning)]


# python -O


def test_invalid_result_under_optimize_flag() -> None:
    """validate_result used assert, which python -O removes. A method that returned
    the wrong type then broke the whole batch.
    """
    code = (
        "import json, logging\n"
        "logging.disable(logging.CRITICAL)\n"
        "from jsonrpcserver import dispatch, Success\n"
        "batch = [{'jsonrpc': '2.0', 'method': 'none', 'id': 1},"
        " {'jsonrpc': '2.0', 'method': 'ping', 'id': 2}]\n"
        "methods = {'none': lambda: None, 'ping': lambda: Success('pong')}\n"
        "print(dispatch(json.dumps(batch), methods))\n"
    )
    output = subprocess.run(
        [sys.executable, "-O", "-c", code], capture_output=True, text=True, check=True
    ).stdout
    assert json.loads(output) == [
        {"jsonrpc": "2.0", "error": INTERNAL_ERROR, "id": 1},
        {"jsonrpc": "2.0", "result": "pong", "id": 2},
    ]


# Property test: whatever comes in, a valid JSON-RPC response goes out


json_values = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=True, allow_infinity=True)
    | st.text(max_size=5),
    lambda children: (
        st.lists(children, max_size=3)
        | st.dictionaries(st.text(max_size=5), children, max_size=3)
    ),
    max_leaves=10,
)
method_names = st.sampled_from([*METHODS, "missing"])
request_members = st.fixed_dictionaries(
    {"jsonrpc": st.sampled_from(["2.0", "1.0"]), "method": method_names},
    optional={
        "params": st.lists(json_values, max_size=2)
        | st.dictionaries(st.text(max_size=3), json_values, max_size=2),
        "id": st.none() | st.integers() | st.text(max_size=3) | st.floats(),
    },
)
requests = (
    request_members | st.lists(request_members | json_values, max_size=4) | json_values
)


def assert_valid_response(response: Any) -> None:
    assert isinstance(response, dict)
    assert response["jsonrpc"] == "2.0"
    assert "id" in response
    assert ("result" in response) != ("error" in response)
    if "error" in response:
        assert isinstance(response["error"]["code"], int)
        assert isinstance(response["error"]["message"], str)


def check(text: str) -> None:
    if text == "":
        return
    parsed = json.loads(
        text, parse_constant=lambda c: pytest.fail(f"Output contains {c}")
    )
    for response in parsed if isinstance(parsed, list) else [parsed]:
        assert_valid_response(response)


@settings(max_examples=300, deadline=None)
@given(requests, st.booleans())
def test_dispatch_always_responds(value: Any, validate: bool) -> None:
    options: Dict[str, Any] = {} if validate else {"validator": lambda _: None}
    check(dispatch(json.dumps(value), METHODS, **options))


@settings(max_examples=100, deadline=None)
@given(st.text(max_size=20))
def test_dispatch_always_responds_to_any_text(text: str) -> None:
    check(dispatch(text, METHODS))


def test_check_rejects_nan() -> None:
    """The property test's own check must catch non-JSON output."""
    with pytest.raises(pytest.fail.Exception):
        check('{"jsonrpc": "2.0", "result": NaN, "id": 1}')
