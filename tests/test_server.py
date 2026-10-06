"""Test server.py"""

from unittest.mock import Mock, patch

from jsonrpcserver.server import serve

# pylint: disable=missing-function-docstring


@patch("jsonrpcserver.server.HTTPServer")
def test_serve(*_: Mock) -> None:
    serve()
