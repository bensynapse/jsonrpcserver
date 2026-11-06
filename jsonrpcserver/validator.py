"""The default validator: checks that a parsed request is a JSON-RPC 2.0 request.

It accepts exactly what the JSON Schema in 5.x accepted (tests/request-schema.json):
an object with "jsonrpc": "2.0" and a string "method", an optional "id" that is a
string, a number or null, optional "params" that is an array or an object, and no
other members. Or a non-empty array of such objects. tests/test_validator.py checks
the two agree. New in 6.0, which dropped the jsonschema dependency.
"""

from typing import Any, cast

_MEMBERS = frozenset({"jsonrpc", "method", "id", "params"})


class InvalidRequestError(ValueError):
    """The parsed request isn't a valid JSON-RPC 2.0 request."""


def _is_number(value: Any) -> bool:
    # JSON Schema's "number" includes integers but not booleans, which are a
    # subclass of int in Python.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def check_request(request: Any) -> None:
    """Raise InvalidRequestError if `request` isn't one valid JSON-RPC 2.0 request."""
    if not isinstance(request, dict):
        raise InvalidRequestError("A request must be an object")
    members = cast(dict[str, Any], request)
    unknown = members.keys() - _MEMBERS
    if unknown:
        raise InvalidRequestError(f"Unknown members: {', '.join(sorted(unknown))}")
    if members.get("jsonrpc") != "2.0" or not isinstance(members["jsonrpc"], str):
        raise InvalidRequestError('"jsonrpc" must be "2.0"')
    if not isinstance(members.get("method"), str):
        raise InvalidRequestError('"method" must be a string')
    if "id" in members:
        id_ = members["id"]
        if not (id_ is None or isinstance(id_, str) or _is_number(id_)):
            raise InvalidRequestError('"id" must be a string, a number or null')
    if "params" in members and not isinstance(members["params"], (list, dict)):
        raise InvalidRequestError('"params" must be an array or an object')


def default_validator(request: Any) -> None:
    """Check a parsed request, or a batch of them, against JSON-RPC 2.0.

    Args:
        request: The parsed request: a dict, or a list of dicts for a batch.

    Raises:
        InvalidRequestError: If it isn't valid. The dispatch functions turn that
            into a -32600 Invalid request response.
    """
    if isinstance(request, list):
        batch = cast(list[object], request)
        if not batch:
            raise InvalidRequestError("A batch must not be empty")
        for member in batch:
            check_request(member)
    else:
        check_request(request)
