"""Responses: what dispatch_to_response gives, and how to turn them into dicts.

A Response is a Result plus the request's id
(https://www.jsonrpc.org/specification#response_object).
"""

from dataclasses import dataclass
from typing import Any

from .codes import (
    ERROR_INVALID_REQUEST,
    ERROR_METHOD_NOT_FOUND,
    ERROR_PARSE_ERROR,
    ERROR_SERVER_ERROR,
)
from .sentinels import NODATA

Deserialized = dict[str, Any] | list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class SuccessResponse:
    """A successful response: the method's result and the request's id."""

    result: Any
    id: Any


@dataclass(frozen=True, slots=True)
class ErrorResponse:
    """An error response: the error's code, message and data, and the request's id.

    `data` is `NODATA` when there's no data, so it's left out of the response. `id`
    is None when the request couldn't be read, as the spec requires.
    """

    code: int
    message: str
    data: Any
    id: Any


# oslash's Either takes the success type first, then the error type.
Response = SuccessResponse | ErrorResponse
"""What `dispatch_to_response` gives for each request.

A `SuccessResponse` or an `ErrorResponse`. Check `isinstance(response, ErrorResponse)`
to tell them apart, or turn one into a dict with `to_dict`. Changed in 6.0: 5.x
wrapped these in oslash's `Right` and `Left`.
"""


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


def to_error_dict(response: ErrorResponse) -> dict[str, Any]:
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


def to_success_dict(response: SuccessResponse) -> dict[str, Any]:
    """Turn a SuccessResponse into a JSON-RPC response dict."""
    return {"jsonrpc": "2.0", "result": response.result, "id": response.id}


def to_dict(response: Response) -> dict[str, Any]:
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
    if isinstance(response, ErrorResponse):
        return to_error_dict(response)
    return to_success_dict(response)


def to_serializable(
    response: Response | list[Response] | None,
) -> Deserialized | None:
    """Turn a Response, a list of them or None into a dict, a list of dicts or None."""
    if response is None:
        return None
    if isinstance(response, list):
        return [to_dict(r) for r in response]
    return to_dict(response)


# The names used in 5.0.9. They were renamed before 5.0.10, and are kept so code that
# imports them keeps working. They will be removed in 6.0.
