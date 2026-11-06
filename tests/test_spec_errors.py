"""Errors for things the JSON-RPC spec doesn't allow. 5.0.10 warned; 6.0 raises."""

import json
import warnings
from typing import Any, cast

import pytest

from jsonrpcserver import Error, JsonRpcError, Result, Success, dispatch, method
from jsonrpcserver.methods import global_methods


@pytest.mark.parametrize(
    "code,message,error",
    [
        ("abc", "msg", "error codes must be integers, not 'abc'"),
        (1.5, "msg", "error codes must be integers, not 1.5"),
        (True, "msg", "error codes must be integers, not True"),
        (1, 5, "error messages must be strings, not 5"),
    ],
)
def test_error_raises(code: Any, message: Any, error: str) -> None:
    with pytest.raises(TypeError, match=error):
        Error(code, message)


@pytest.mark.parametrize(
    "code,message,error",
    [
        ("abc", "msg", "error codes must be integers"),
        (1, None, "error messages must be strings"),
    ],
)
def test_jsonrpcerror_raises(code: Any, message: Any, error: str) -> None:
    with pytest.raises(TypeError, match=error):
        JsonRpcError(code, message)


def test_valid_errors_dont_raise_or_warn() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Error(1, "msg")
        Error(code=-32000, message="msg", data={"x": 1})
        JsonRpcError(1, "msg")


def test_a_bad_error_in_a_method_is_an_internal_error() -> None:
    def fail() -> Result:
        return Error(cast(Any, "abc"), "msg")

    response = dispatch('{"jsonrpc": "2.0", "method": "fail", "id": 1}', {"fail": fail})
    assert json.loads(response)["error"]["code"] == -32603


def test_rpc_prefix_raises() -> None:
    with pytest.raises(ValueError, match="reserved by the JSON-RPC spec"):

        @method(name="rpc.discover")
        def discover() -> Result:
            return Success()

    assert "rpc.discover" not in global_methods


def test_rpc_prefix_raises_bare_decorator() -> None:
    def f() -> Result:
        return Success()

    f.__name__ = "rpc.x"
    with pytest.raises(ValueError, match=r"'rpc\.x'"):
        method(f)
    assert "rpc.x" not in global_methods


def test_normal_name_doesnt_raise_or_warn() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")

        @method(name="rpcx")
        def f() -> Result:
            return Success()

    del global_methods["rpcx"]
