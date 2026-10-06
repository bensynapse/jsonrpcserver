"""Process incoming JSON-RPC requests in Python.

Write methods with @method, then pass each request string to dispatch, or to
async_dispatch in an asyncio server. Documentation:
https://bensynapse.github.io/jsonrpcserver/
"""

# __all__ also tells type checkers that these names are re-exported.
__all__ = [
    "Error",
    "InvalidParams",
    "JsonRpcError",
    "Result",
    "Success",
    "async_dispatch",
    "async_dispatch_to_response",
    "async_dispatch_to_serializable",
    "dispatch",
    "dispatch_to_response",
    "dispatch_to_serializable",
    "method",
    "serve",
]


from .async_main import (
    dispatch as async_dispatch,
)
from .async_main import (
    dispatch_to_response as async_dispatch_to_response,
)
from .async_main import (
    dispatch_to_serializable as async_dispatch_to_serializable,
)
from .exceptions import JsonRpcError
from .main import dispatch, dispatch_to_response, dispatch_to_serializable
from .methods import method
from .result import Error, InvalidParams, Result, Success
from .server import serve

__version__ = "5.0.10"
"""The version of jsonrpcserver, as a string. Added in 5.0.10."""
