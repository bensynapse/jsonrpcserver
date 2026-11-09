"""Rules from the JSON-RPC 2.0 spec that docs/spec.md lists and no other test
shows directly. https://www.jsonrpc.org/specification
"""

import json
import warnings
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from jsonrpcserver import Error, JsonRpcError, Result, Success, dispatch, method
from jsonrpcserver.methods import global_methods

INVALID_REQUEST = {
    "jsonrpc": "2.0",
    "error": {
        "code": -32600,
        "message": "Invalid request",
        "data": "The request failed schema validation",
    },
    "id": None,
}


def ping() -> Result:
    return Success("pong")


def colour(colour: str) -> Result:
    return Success(colour)


def take(value: float) -> Result:
    return Success("taken")


def busy() -> Result:
    return Error(-32050, "Busy")


def fail() -> Result:
    raise ValueError("fail")


METHODS: Dict[str, Any] = {"ping": ping, "colour": colour, "busy": busy, "fail": fail}


def send(request: Any) -> Any:
    return json.loads(dispatch(json.dumps(request), METHODS))


@pytest.mark.parametrize("id_", ["abc", 1, 1.5, -2, None])
def test_id_is_returned_unchanged(id_: Any) -> None:
    """Section 4: the server must reply with the same id value. Null and
    fractional ids are discouraged but allowed."""
    request = json.dumps({"jsonrpc": "2.0", "method": "ping", "id": id_})
    # Compare the text, so an id of 1 sent back as 1.0 fails.
    assert dispatch(request, METHODS) == (
        f'{{"jsonrpc": "2.0", "result": "pong", "id": {json.dumps(id_)}}}'
    )


@pytest.mark.parametrize("id_", [True, False, [], [1], {}, {"a": 1}])
def test_id_that_is_not_a_string_number_or_null(id_: Any) -> None:
    """Section 4: an id must be a String, Number or Null."""
    assert send({"jsonrpc": "2.0", "method": "ping", "id": id_}) == INVALID_REQUEST


@pytest.mark.parametrize("version", ["1.0", "2", 2.0, 2, None])
def test_jsonrpc_must_be_exactly_2_0(version: Any) -> None:
    """Section 4: "jsonrpc" must be exactly "2.0"."""
    assert send({"jsonrpc": version, "method": "ping", "id": 1}) == INVALID_REQUEST


@pytest.mark.parametrize("method", [1, None, [], {}])
def test_method_must_be_a_string(method: Any) -> None:
    """Section 4: "method" is a String."""
    assert send({"jsonrpc": "2.0", "method": method, "id": 1}) == INVALID_REQUEST


def test_member_names_are_case_sensitive() -> None:
    """Section 2: member names are case-sensitive. "JSONRPC" isn't "jsonrpc"."""
    assert send({"JSONRPC": "2.0", "method": "ping", "id": 1}) == INVALID_REQUEST


def test_jsonrpc_member_is_required() -> None:
    """Section 3: a 1.0 request has no "jsonrpc" member. It isn't handled."""
    assert send({"method": "ping", "params": [], "id": 1}) == INVALID_REQUEST


@pytest.mark.parametrize("params", ["blue", 1, True, None])
def test_params_must_be_structured(params: Any) -> None:
    """Section 4.2: params, if present, must be an Array or an Object."""
    request = {"jsonrpc": "2.0", "method": "colour", "params": params, "id": 1}
    assert send(request) == INVALID_REQUEST


def test_params_by_name_match_case() -> None:
    """Section 4.2: names must match exactly, including case."""
    request = {"jsonrpc": "2.0", "method": "colour", "params": {"Colour": "x"}, "id": 1}
    assert send(request)["error"]["code"] == -32602
    request["params"] = {"colour": "x"}
    assert send(request)["result"] == "x"


def test_unknown_members_are_an_invalid_request() -> None:
    """The spec doesn't say what to do with other members. jsonrpcserver
    rejects them, as 5.x's schema did."""
    request = {"jsonrpc": "2.0", "method": "ping", "id": 1, "extra": 1}
    assert send(request) == INVALID_REQUEST


def test_rpc_names_in_a_methods_dict_are_called() -> None:
    """Section 4: names starting with "rpc." are reserved. @method warns about
    them (tests/test_warnings.py), but a dict you pass yourself isn't checked."""
    request = '{"jsonrpc": "2.0", "method": "rpc.ping", "id": 1}'
    assert json.loads(dispatch(request, {"rpc.ping": ping}))["result"] == "pong"


def test_server_error_range_is_passed_through() -> None:
    """Section 5.1: -32000 to -32099 are for implementation-defined server
    errors. A method may return one, and it's sent unchanged."""
    assert send({"jsonrpc": "2.0", "method": "busy", "id": 1}) == {
        "jsonrpc": "2.0",
        "error": {"code": -32050, "message": "Busy"},
        "id": 1,
    }


def test_failing_notifications_in_a_batch_get_no_response() -> None:
    """Sections 4.1 and 6: no reply to a notification, even in a batch and even
    when it fails. A batch with nothing to send gets nothing at all."""
    batch: List[Dict[str, Any]] = [
        {"jsonrpc": "2.0", "method": "missing"},
        {"jsonrpc": "2.0", "method": "colour", "params": []},
        {"jsonrpc": "2.0", "method": "fail"},
    ]
    assert dispatch(json.dumps(batch), METHODS) == ""


@pytest.mark.parametrize("request_", ["1", '"ping"', "true", "null"])
def test_json_that_is_not_an_object_or_array(request_: str) -> None:
    """Section 6: if the call isn't an Array with at least one value, the
    response is a single Response object, not an Array."""
    assert json.loads(dispatch(request_, METHODS)) == INVALID_REQUEST


@pytest.mark.parametrize(
    "code,message", [("abc", "msg"), (1.5, "msg"), (True, "msg"), (1, 5)]
)
def test_a_bad_error_is_sent_as_given(code: Any, message: Any) -> None:
    """Section 5.1: code must be an integer and message a String. 5.x warns
    when the error is made, and sends it anyway. 6.0 raises TypeError."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        error = Error(code, message)
    request = '{"jsonrpc": "2.0", "method": "bad", "id": 1}'
    response = json.loads(dispatch(request, {"bad": lambda: error}))
    assert response["error"] == {"code": code, "message": message}
    # True == 1 in Python, so check the type too.
    assert type(response["error"]["code"]) is type(code)


def test_a_bad_jsonrpcerror_is_sent_as_given() -> None:
    """The same for JsonRpcError raised in a method."""

    def bad() -> Result:
        raise JsonRpcError(True, "msg")

    request = '{"jsonrpc": "2.0", "method": "bad", "id": 1}'
    with pytest.warns(UserWarning, match="error codes must be integers"):
        response = dispatch(request, {"bad": bad})
    assert '"error": {"code": true, "message": "msg"}' in response


def test_rpc_names_registered_with_method_are_called() -> None:
    """Section 4: "rpc." names are reserved. In 5.x, @method warns and
    registers the method anyway, so a request can call it."""
    with pytest.warns(UserWarning, match="reserved by the JSON-RPC spec"):

        @method(name="rpc.ping")
        def rpc_ping() -> Result:
            return Success("pong")

    try:
        response = dispatch('{"jsonrpc": "2.0", "method": "rpc.ping", "id": 1}')
        assert json.loads(response)["result"] == "pong"
    finally:
        del global_methods["rpc.ping"]


@patch("jsonrpcserver.dispatcher.dispatch_request", side_effect=ValueError("bug"))
def test_server_error_in_a_batch_keeps_member_ids(_: Any) -> None:
    """If jsonrpcserver itself fails on a batch member, that member gets -32000
    with its own id. A notification gets one too, with a null id: the
    deviation docs/spec.md lists."""
    batch = [
        {"jsonrpc": "2.0", "method": "ping", "id": 7},
        {"jsonrpc": "2.0", "method": "ping"},
    ]
    error = {"code": -32000, "message": "Server error"}
    assert json.loads(dispatch(json.dumps(batch), METHODS)) == [
        {"jsonrpc": "2.0", "error": error, "id": 7},
        {"jsonrpc": "2.0", "error": error, "id": None},
    ]


def test_methods_can_use_reserved_codes() -> None:
    """Section 5.1: -32768 to -32000 are reserved. A method can still return
    one of them, and it's sent unchanged."""
    request = '{"jsonrpc": "2.0", "method": "reserved", "id": 1}'
    response = dispatch(request, {"reserved": lambda: Error(-32601, "Mine")})
    assert json.loads(response)["error"] == {"code": -32601, "message": "Mine"}


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_json_constants_are_accepted(constant: str) -> None:
    """NaN and Infinity aren't JSON (RFC 8259), so they should get -32700.
    5.x reads them and calls the method, with a FutureWarning. 6.0 sends
    -32700."""
    request = (
        '{"jsonrpc": "2.0", "method": "take", "params": [' + constant + '], "id": 1}'
    )
    with pytest.warns(FutureWarning):
        response = dispatch(request, {"take": take})
    assert json.loads(response) == {"jsonrpc": "2.0", "result": "taken", "id": 1}


def test_infinite_id_runs_the_method_first() -> None:
    """An id like 1e400 is read as infinity. The method runs, then the response
    can't be serialized, so the client gets -32603 with a null id."""
    calls: List[int] = []

    def record() -> Result:
        calls.append(1)
        return Success()

    request = '{"jsonrpc": "2.0", "method": "record", "id": 1e400}'
    with pytest.warns(FutureWarning):
        response = json.loads(dispatch(request, {"record": record}))
    assert calls == [1]
    assert response == {
        "jsonrpc": "2.0",
        "error": {"code": -32603, "message": "Internal error"},
        "id": None,
    }
