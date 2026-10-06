"""What a method returns: Success, Error or InvalidParams.

A Result is the "result" or "error" part of a JSON-RPC response object
(https://www.jsonrpc.org/specification#response_object). The library adds the
"jsonrpc" and "id" parts.
"""

from typing import Any, NamedTuple

from oslash.either import Either, Left, Right

from .codes import ERROR_INTERNAL_ERROR, ERROR_INVALID_PARAMS, ERROR_METHOD_NOT_FOUND
from .sentinels import NODATA
from .utils import warn_if_invalid_error

# pylint: disable=missing-class-docstring,missing-function-docstring,invalid-name


class SuccessResult(NamedTuple):
    """The value inside the Result that `Success` returns."""

    result: Any = None

    def __repr__(self) -> str:
        return f"SuccessResult({self.result!r})"


class ErrorResult(NamedTuple):
    """The value inside the Result that `Error` and `InvalidParams` return.

    `data` is `NODATA` when there's no data, so it's left out of the response.
    """

    code: int
    message: str
    data: Any = NODATA  # The spec says this value may be omitted

    def __repr__(self) -> str:
        return (
            f"ErrorResult(code={self.code!r}, message={self.message!r}, "
            f"data={self.data!r})"
        )


# Union of the two valid result types. oslash's Either takes the success type
# first, then the error type.
Result = Either[SuccessResult, ErrorResult]
"""The return type of a method: what `Success`, `Error` and `InvalidParams` give.

It's an oslash `Either`: a `Right` holding a `SuccessResult`, or a `Left` holding an
`ErrorResult`. Use it as the return annotation of your methods. You don't need to
look inside it.
"""


# Helpers


def MethodNotFoundResult(data: Any) -> ErrorResult:
    return ErrorResult(ERROR_METHOD_NOT_FOUND, "Method not found", data)


def InternalErrorResult(data: Any) -> ErrorResult:
    return ErrorResult(ERROR_INTERNAL_ERROR, "Internal error", data)


def InvalidParamsResult(data: Any = NODATA) -> ErrorResult:
    return ErrorResult(ERROR_INVALID_PARAMS, "Invalid params", data)


# Helpers (the public functions)


def Success(result: Any = None) -> Result:
    """A successful result. Return it from a method.

    Args:
        result: The value for the response's `result` member. It can be anything
            the serializer handles. The default, None, is sent as `null`.

    Returns:
        A Result holding the value.

    Example:
        >>> from jsonrpcserver import Result, Success, dispatch
        >>> def ping() -> Result:
        ...     return Success("pong")
        >>> dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}', {"ping": ping})
        '{"jsonrpc": "2.0", "result": "pong", "id": 1}'
    """
    return Right(SuccessResult(result))


def Error(code: int, message: str, data: Any = NODATA) -> Result:
    """An error result. Return it from a method to send an error response.

    It's sent as it is, whatever `debug` is, so don't put secrets in it.

    Args:
        code: The error code, an integer. The spec reserves -32768 to -32000 for
            its own errors, so pick other numbers for yours.
        message: A short description of the error, as a string.
        data: Extra information for the client, such as details of what went
            wrong. If it isn't given, the response has no `data` member.

    Returns:
        A Result holding the error.

    Warns:
        UserWarning: If `code` isn't an int or `message` isn't a str. The error is
            still sent as given. New in 5.0.10.

    Example:
        >>> from jsonrpcserver import Error, Result, dispatch_to_serializable
        >>> def fail() -> Result:
        ...     return Error(1, "It failed", {"reason": "example"})
        >>> request = '{"jsonrpc": "2.0", "method": "fail", "id": 1}'
        >>> dispatch_to_serializable(request, {"fail": fail})["error"]
        {'code': 1, 'message': 'It failed', 'data': {'reason': 'example'}}
    """
    warn_if_invalid_error(code, message, stacklevel=2)
    return Left(ErrorResult(code, message, data))


def InvalidParams(data: Any = NODATA) -> Result:
    """An Invalid params error: `Error(-32602, "Invalid params", data)`.

    Return it when the arguments have the right shape but a bad value.
    jsonrpcserver already sends this error when the arguments don't fit the
    method's signature.

    Args:
        data: What was wrong, for the client. If it isn't given, the response has no
            `data` member.

    Returns:
        A Result holding the error.

    Example:
        >>> from jsonrpcserver import InvalidParams, Result, Success
        >>> from jsonrpcserver import dispatch_to_serializable
        >>> def rate(stars: int) -> Result:
        ...     if stars not in range(1, 6):
        ...         return InvalidParams("Stars must be 1 to 5")
        ...     return Success()
        >>> request = '{"jsonrpc": "2.0", "method": "rate", "params": [6], "id": 1}'
        >>> dispatch_to_serializable(request, {"rate": rate})["error"]
        {'code': -32602, 'message': 'Invalid params', 'data': 'Stars must be 1 to 5'}
    """
    return Left(InvalidParamsResult(data))
