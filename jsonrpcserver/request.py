"""A simple namedtuple to hold a request.

After parsing a request string, we put the (dict) requests into these Request
namedtuples, simply because they're nicer to work with.
"""

from typing import Any, NamedTuple


class Request(NamedTuple):
    """JSON-RPC Request"""

    method: str
    params: list[Any] | dict[str, Any]
    id: Any  # Use NOID for a Notification.
