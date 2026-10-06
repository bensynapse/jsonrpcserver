"""Warnings for things the JSON-RPC spec doesn't allow."""

import warnings
from typing import Any

import pytest

from jsonrpcserver import Error, JsonRpcError, Result, Success, method
from jsonrpcserver.methods import global_methods


@pytest.mark.parametrize(
    "code,message,warning",
    [
        ("abc", "msg", "error codes must be integers, not 'abc'"),
        (1.5, "msg", "error codes must be integers, not 1.5"),
        (True, "msg", "error codes must be integers, not True"),
        (1, 5, "error messages should be strings, not 5"),
    ],
)
def test_error_warns(code: Any, message: Any, warning: str) -> None:
    with pytest.warns(UserWarning, match=warning) as record:
        Error(code, message)
    assert record[0].filename == __file__


@pytest.mark.parametrize(
    "code,message,warning",
    [
        ("abc", "msg", "error codes must be integers"),
        (1, None, "error messages should be strings"),
    ],
)
def test_jsonrpcerror_warns(code: Any, message: Any, warning: str) -> None:
    with pytest.warns(UserWarning, match=warning) as record:
        JsonRpcError(code, message)
    assert record[0].filename == __file__


def test_valid_errors_dont_warn() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Error(1, "msg")
        Error(code=-32000, message="msg", data={"x": 1})
        JsonRpcError(1, "msg")


def test_rpc_prefix_warns() -> None:
    with pytest.warns(UserWarning, match="reserved by the JSON-RPC spec") as record:

        @method(name="rpc.discover")
        def discover() -> Result:
            return Success()

    assert record[0].filename == __file__
    del global_methods["rpc.discover"]


def test_rpc_prefix_warns_bare_decorator() -> None:
    with pytest.warns(UserWarning, match="'rpc.x'") as record:

        def f() -> Result:
            return Success()

        f.__name__ = "rpc.x"
        method(f)

    assert record[0].filename == __file__
    del global_methods["rpc.x"]


def test_normal_name_doesnt_warn() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")

        @method(name="rpcx")
        def f() -> Result:
            return Success()

    del global_methods["rpcx"]
