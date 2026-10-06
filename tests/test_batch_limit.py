"""max_batch_size"""

import json
from typing import Any, List

import pytest

from jsonrpcserver import Result, Success, async_dispatch, dispatch
from jsonrpcserver.main import dispatch_to_response

calls: List[int] = []


def ping() -> Result:
    calls.append(1)
    return Success("pong")


async def aping() -> Result:
    calls.append(1)
    return Success("pong")


def batch(size: int, notification: bool = False) -> str:
    return json.dumps(
        [
            {"jsonrpc": "2.0", "method": "ping", **({} if notification else {"id": i})}
            for i in range(size)
        ]
    )


TOO_LARGE = {
    "jsonrpc": "2.0",
    "error": {
        "code": -32600,
        "message": "Invalid request",
        "data": "The batch has 3 requests. The limit is 2.",
    },
    "id": None,
}


@pytest.fixture(autouse=True)
def reset_calls() -> None:
    calls.clear()


def test_no_limit_by_default() -> None:
    assert len(json.loads(dispatch(batch(500), {"ping": ping}))) == 500


def test_at_the_limit() -> None:
    assert len(json.loads(dispatch(batch(2), {"ping": ping}, max_batch_size=2))) == 2


def test_over_the_limit() -> None:
    response = dispatch(batch(3), {"ping": ping}, max_batch_size=2)
    assert json.loads(response) == TOO_LARGE
    assert calls == []


def test_over_the_limit_notifications() -> None:
    """Even a batch of notifications gets the error, since nothing is dispatched."""
    response = dispatch(batch(3, notification=True), {"ping": ping}, max_batch_size=2)
    assert json.loads(response) == TOO_LARGE
    assert calls == []


def test_single_request_ignores_limit() -> None:
    response = dispatch(
        '{"jsonrpc": "2.0", "method": "ping", "id": 1}',
        {"ping": ping},
        max_batch_size=1,
    )
    assert json.loads(response)["result"] == "pong"


def test_dispatch_to_response_over_the_limit() -> None:
    response: Any = dispatch_to_response(batch(3), {"ping": ping}, max_batch_size=2)
    assert response._error.code == -32600


@pytest.mark.asyncio
async def test_async_over_the_limit() -> None:
    response = await async_dispatch(batch(3), {"ping": aping}, max_batch_size=2)
    assert json.loads(response) == TOO_LARGE
    assert calls == []


@pytest.mark.asyncio
async def test_async_at_the_limit() -> None:
    response = await async_dispatch(batch(2), {"ping": aping}, max_batch_size=2)
    assert len(json.loads(response)) == 2


@pytest.mark.parametrize("value", [0, -1, 1.5, "10", True])
def test_bad_limit(value: Any) -> None:
    with pytest.raises(ValueError, match="max_batch_size must be a positive int"):
        dispatch(batch(1), {"ping": ping}, max_batch_size=value)


@pytest.mark.asyncio
async def test_async_bad_limit() -> None:
    with pytest.raises(ValueError, match="max_batch_size must be a positive int"):
        await async_dispatch(batch(1), {"ping": aping}, max_batch_size=0)


def test_validator_sees_members_not_the_batch() -> None:
    """Since #291 a custom validator gets each member on its own. A batch-level rule
    belongs in max_batch_size.
    """
    seen: List[Any] = []

    def validator(request: Any) -> None:
        seen.append(request)

    dispatch(batch(2), {"ping": ping}, validator=validator)
    assert [type(item) for item in seen] == [dict, dict]
