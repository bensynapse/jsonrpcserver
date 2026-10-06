"""__version__ must match the installed package metadata."""

from importlib.metadata import version

import jsonrpcserver


def test_version() -> None:
    assert jsonrpcserver.__version__ == version("jsonrpcserver")
