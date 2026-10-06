"""A simple namedtuple to hold a request.

After parsing a request string, we put the (dict) requests into these Request
namedtuples, simply because they're nicer to work with.
"""

from typing import Any, Dict, List, NamedTuple, Union


class Request(NamedTuple):
    """JSON-RPC Request"""

    method: str
    params: Union[List[Any], Dict[str, Any]]
    id: Any  # Use NOID for a Notification.
