"""Responses: what dispatch_to_response gives, and how to turn them into dicts.

A Response is a Result plus the request's id
(https://www.jsonrpc.org/specification#response_object).
"""

import warnings
from typing import Any, Dict, List, NamedTuple, Type, Union, cast

from oslash.either import Either, Left, Right

from .codes import (
    ERROR_INVALID_REQUEST,
    ERROR_METHOD_NOT_FOUND,
    ERROR_PARSE_ERROR,
    ERROR_SERVER_ERROR,
)
from .sentinels import NODATA

Deserialized = Union[Dict[str, Any], List[Dict[str, Any]]]


class SuccessResponse(NamedTuple):
    """A successful response: the method's result and the request's id."""

    result: Any
    id: Any


class ErrorResponse(NamedTuple):
    """An error response: the error's code, message and data, and the request's id.

    `data` is `NODATA` when there's no data, so it's left out of the response. `id`
    is None when the request couldn't be read, as the spec requires.
    """

    code: int
    message: str
    data: Any
    id: Any


# oslash's Either takes the success type first, then the error type.
Response = Either[SuccessResponse, ErrorResponse]
"""What `dispatch_to_response` gives for each request.

An oslash `Either`: a `Right` holding a `SuccessResponse`, or a `Left` holding an
`ErrorResponse`. To read one, check `isinstance(response, Left)`, then read
`response._error` (an `ErrorResponse`) or `response._value` (a `SuccessResponse`).
oslash has no public accessor, but these attributes are stable for all of 5.x. Or turn
it into a dict with `to_dict`.
"""
ResponseType = Type[Response]
"""Deprecated: use `Response`. Kept so code written for 5.0.9 keeps working."""


def ParseErrorResponse(data: Any) -> ErrorResponse:  # pylint: disable=invalid-name
    """An ErrorResponse with most attributes already populated.

    From the spec: "This (id) member is REQUIRED. It MUST be the same as the value of
    the id member in the Request Object.  If there was an error in detecting the id in
    the Request object (e.g. Parse error/Invalid Request), it MUST be Null."
    """
    return ErrorResponse(ERROR_PARSE_ERROR, "Parse error", data, None)


def InvalidRequestResponse(data: Any) -> ErrorResponse:  # pylint: disable=invalid-name
    """An ErrorResponse with most attributes already populated.

    From the spec: "This (id) member is REQUIRED. It MUST be the same as the value of
    the id member in the Request Object.  If there was an error in detecting the id in
    the Request object (e.g. Parse error/Invalid Request), it MUST be Null."
    """
    return ErrorResponse(ERROR_INVALID_REQUEST, "Invalid request", data, None)


def MethodNotFoundResponse(data: Any, id: Any) -> ErrorResponse:
    """An ErrorResponse with some attributes already populated."""
    # pylint: disable=invalid-name,redefined-builtin
    return ErrorResponse(ERROR_METHOD_NOT_FOUND, "Method not found", data, id)


def ServerErrorResponse(data: Any, id: Any) -> ErrorResponse:
    """An ErrorResponse with some attributes already populated."""
    # pylint: disable=invalid-name,redefined-builtin
    return ErrorResponse(ERROR_SERVER_ERROR, "Server error", data, id)


def to_error_dict(response: ErrorResponse) -> Dict[str, Any]:
    """Turn an ErrorResponse into a JSON-RPC response dict, leaving out missing data."""
    return {
        "jsonrpc": "2.0",
        "error": {
            "code": response.code,
            "message": response.message,
            # "data" may be omitted.
            **({"data": response.data} if response.data is not NODATA else {}),
        },
        "id": response.id,
    }


def to_success_dict(response: SuccessResponse) -> Dict[str, Any]:
    """Turn a SuccessResponse into a JSON-RPC response dict."""
    return {"jsonrpc": "2.0", "result": response.result, "id": response.id}


def to_dict(response: Response) -> Dict[str, Any]:
    """Turn a Response into a JSON-RPC response dict.

    Args:
        response: A Response from `dispatch_to_response`.

    Returns:
        The response as a dict, ready for `json.dumps`.

    Example:
        >>> from jsonrpcserver import Result, Success, dispatch_to_response
        >>> def ping() -> Result:
        ...     return Success("pong")
        >>> request = '{"jsonrpc": "2.0", "method": "ping", "id": 1}'
        >>> to_dict(dispatch_to_response(request, {"ping": ping}))
        {'jsonrpc': '2.0', 'result': 'pong', 'id': 1}
    """
    if isinstance(response, Left):
        return to_error_dict(response._error)
    success = cast("Right[SuccessResponse, ErrorResponse]", response)
    return to_success_dict(success._value)


def to_serializable(
    response: Union[Response, List[Response], None],
) -> Union[Deserialized, None]:
    """Turn a Response, a list of them or None into a dict, a list of dicts or None."""
    if response is None:
        return None
    if isinstance(response, List):
        return [to_dict(r) for r in response]
    return to_dict(response)


# The names used in 5.0.9. They were renamed before 5.0.10, and are kept so code that
# imports them keeps working. They will be removed in 6.0.


def _deprecated(old: str, new: str) -> None:
    warnings.warn(
        f"jsonrpcserver.response.{old} is deprecated and will be removed in 6.0. "
        f"Use {new} instead.",
        DeprecationWarning,
        stacklevel=3,
    )


def serialize_error(response: ErrorResponse) -> Dict[str, Any]:
    """Deprecated: use `to_error_dict`. Warns with DeprecationWarning (5.0.10)."""
    _deprecated("serialize_error", "to_error_dict")
    return to_error_dict(response)


def serialize_success(response: SuccessResponse) -> Dict[str, Any]:
    """Deprecated: use `to_success_dict`. Warns with DeprecationWarning (5.0.10)."""
    _deprecated("serialize_success", "to_success_dict")
    return to_success_dict(response)


def to_serializable_one(response: Response) -> Dict[str, Any]:
    """Deprecated: use `to_dict`. Warns with DeprecationWarning (5.0.10)."""
    _deprecated("to_serializable_one", "to_dict")
    return to_dict(response)
