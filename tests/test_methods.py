"""Test methods.py"""

import pytest

from jsonrpcserver import Result, Success, dispatch
from jsonrpcserver.methods import global_methods, method

# pylint: disable=missing-function-docstring


def test_decorator() -> None:
    @method
    def func() -> None:
        pass

    assert callable(global_methods["func"])


def test_decorator_custom_name() -> None:
    @method(name="new_name")
    def name() -> None:
        pass

    assert callable(global_methods["new_name"])


def test_decorator_empty_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(global_methods, "", lambda: Success("previous"))

    @method(name="")
    def empty_name() -> Result:
        return Success("pong")

    assert dispatch('{"jsonrpc": "2.0", "method": "", "id": 1}') == (
        '{"jsonrpc": "2.0", "result": "pong", "id": 1}'
    )
    assert global_methods[""] is empty_name
