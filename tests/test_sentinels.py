"""Test sentinels.py"""

from jsonrpcserver.sentinels import Sentinel

# pylint: disable=missing-function-docstring


def test_sentinel() -> None:
    assert repr(Sentinel("foo")) == "<foo>"
