"""5.2.0 warns about the 5.x behaviour that 6.0 changes (plans/6.0.md, D12)."""

import json
import warnings
from unittest.mock import Mock, patch

import pytest

from jsonrpcserver import Result, Success, dispatch, serve

METHODS = {"ping": lambda: Success("pong")}


def take_one(x: float) -> Result:
    return Success()


def take_two(a: float, b: float) -> Result:
    return Success()


def batch(size: int) -> str:
    return json.dumps(
        [{"jsonrpc": "2.0", "method": "ping", "id": n} for n in range(size)]
    )


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_json_constants_warn(constant: str) -> None:
    request = (
        '{"jsonrpc": "2.0", "method": "ping", "params": [' + constant + '], "id": 1}'
    )
    with pytest.warns(FutureWarning, match=f"{constant} in a request isn't valid JSON"):
        dispatch(request, {"ping": take_one})


def test_json_loads_accepts_them_quietly() -> None:
    request = '{"jsonrpc": "2.0", "method": "ping", "params": [NaN], "id": 1}'
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        dispatch(request, {"ping": take_one}, deserializer=json.loads)


def test_ordinary_numbers_dont_warn() -> None:
    request = '{"jsonrpc": "2.0", "method": "ping", "params": [1.5, 1e300], "id": 1}'
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        dispatch(request, {"ping": take_two})


def test_batch_of_100_doesnt_warn() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        dispatch(batch(100), METHODS)


def test_batch_of_101_warns() -> None:
    with pytest.warns(FutureWarning, match="This batch has 101 requests"):
        dispatch(batch(101), METHODS)


@pytest.mark.asyncio
async def test_async_batch_of_101_warns() -> None:
    from jsonrpcserver import async_dispatch

    with pytest.warns(FutureWarning, match="This batch has 101 requests"):
        await async_dispatch(batch(101), METHODS)


def test_explicit_limit_doesnt_warn() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        dispatch(batch(101), METHODS, max_batch_size=200)


@patch("jsonrpcserver.server.ThreadingHTTPServer")
def test_serve_with_a_host_doesnt_warn(server: Mock) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        serve("", 5000)
        serve("localhost", 5000)
