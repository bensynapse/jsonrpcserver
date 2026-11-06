"""The built-in validator accepts exactly what 5.x's JSON Schema accepted."""

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from jsonschema import Draft4Validator

from jsonrpcserver.validator import InvalidRequestError, default_validator

SCHEMA = json.loads((Path(__file__).parent / "request-schema.json").read_text())
SCHEMA_VALIDATOR = Draft4Validator(SCHEMA)


def schema_accepts(request: Any) -> bool:
    return SCHEMA_VALIDATOR.is_valid(request)  # pyright: ignore[reportUnknownMemberType]


def validator_accepts(request: Any) -> bool:
    try:
        default_validator(request)
    except InvalidRequestError:
        return False
    return True


REQUEST = {"jsonrpc": "2.0", "method": "ping"}

CASES: list[Any] = [
    REQUEST,
    {**REQUEST, "id": 1},
    {**REQUEST, "id": 1.5},
    {**REQUEST, "id": "a"},
    {**REQUEST, "id": None},
    {**REQUEST, "id": True},
    {**REQUEST, "id": []},
    {**REQUEST, "id": {}},
    {**REQUEST, "params": []},
    {**REQUEST, "params": {}},
    {**REQUEST, "params": [1, {"a": None}]},
    {**REQUEST, "params": "x"},
    {**REQUEST, "params": None},
    {**REQUEST, "params": 1},
    {**REQUEST, "extra": 1},
    {"jsonrpc": "2.0"},
    {"method": "ping"},
    {"jsonrpc": "1.0", "method": "ping"},
    {"jsonrpc": 2.0, "method": "ping"},
    {"jsonrpc": "2.0", "method": 1},
    {"jsonrpc": "2.0", "method": None},
    {"jsonrpc": "2.0", "method": ""},
    {},
    [],
    [REQUEST],
    [REQUEST, {**REQUEST, "id": 2}],
    [REQUEST, 1],
    [[]],
    [[REQUEST]],
    1,
    "x",
    None,
    True,
]


@pytest.mark.parametrize("request_", CASES)
def test_agrees_with_the_5x_schema(request_: Any) -> None:
    assert validator_accepts(request_) == schema_accepts(request_)


json_values = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=5),
    lambda inner: (
        st.lists(inner, max_size=3)
        | st.dictionaries(st.text(max_size=5), inner, max_size=3)
    ),
    max_leaves=10,
)
member_values = st.sampled_from(["2.0", "1.0", "ping", ""]) | json_values
requestish = st.dictionaries(
    st.sampled_from(["jsonrpc", "method", "id", "params", "extra"]),
    member_values,
    max_size=5,
)


@settings(max_examples=500)
@given(st.one_of(requestish, st.lists(requestish, max_size=3), json_values))
def test_agrees_with_the_5x_schema_on_generated_input(request_: Any) -> None:
    assert validator_accepts(request_) == schema_accepts(request_)


def test_messages_say_what_is_wrong() -> None:
    with pytest.raises(InvalidRequestError, match="Unknown members: extra"):
        default_validator({**REQUEST, "extra": 1})
    with pytest.raises(InvalidRequestError, match="must not be empty"):
        default_validator([])
