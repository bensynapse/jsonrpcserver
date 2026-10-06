"""Exceptions"""

from typing import Any

from .sentinels import NODATA
from .utils import warn_if_invalid_error


class JsonRpcError(Exception):
    """A JsonRpcError exception can be raised from inside a method, as an alternate way
    to return an error response. See
    https://github.com/explodinglabs/jsonrpcserver/discussions/158
    """

    def __init__(self, code: int, message: str, data: Any = NODATA):
        warn_if_invalid_error(code, message, stacklevel=2)
        self.code, self.message, self.data = (code, message, data)
