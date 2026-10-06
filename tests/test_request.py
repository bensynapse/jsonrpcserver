"""Test request.py"""

from jsonrpcserver.request import Request

# pylint: disable=missing-function-docstring


def test_request() -> None:
    assert Request(method="foo", params=[], id=1).method == "foo"


def test_request_invalid() -> None:
    # Should never happen, because the incoming request string is passed through the
    # jsonrpc schema before creating a Request
    pass
