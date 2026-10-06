"""The exception a method can raise to send an error response."""

from typing import Any

from .sentinels import NODATA
from .utils import warn_if_invalid_error


class JsonRpcError(Exception):
    """Raise it in a method, or in anything a method calls, to send an error response.

    It's the same as returning `Error(code, message, data)`, but it works from deep
    inside other functions. Like `Error`, it's sent as it is, whatever `debug` is.

    Args:
        code: The error code, an integer.
        message: A short description of the error, as a string.
        data: Extra information for the client. If it isn't given, the response has
            no `data` member.

    Warns:
        UserWarning: If `code` isn't an int or `message` isn't a str. New in 5.0.10.

    Example:
        >>> from jsonrpcserver import Result, dispatch_to_serializable
        >>> def withdraw(amount: int) -> Result:
        ...     raise JsonRpcError(2, "Insufficient funds", {"balance": 10})
        >>> request = '{"jsonrpc": "2.0", "method": "withdraw", "params": [5], "id": 1}'
        >>> dispatch_to_serializable(request, {"withdraw": withdraw})["error"]
        {'code': 2, 'message': 'Insufficient funds', 'data': {'balance': 10}}
    """

    def __init__(self, code: int, message: str, data: Any = NODATA):
        warn_if_invalid_error(code, message, stacklevel=2)
        self.code, self.message, self.data = (code, message, data)
