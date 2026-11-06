"""async_dispatch's max_concurrency (plans/6.0.md, D8)."""

import asyncio
import json
from typing import Any

import pytest

from jsonrpcserver import async_dispatch

BATCH = json.dumps(
    [{"jsonrpc": "2.0", "method": "slow", "id": n} for n in range(1, 11)]
)


class Tracker:
    def __init__(self) -> None:
        self.running = 0
        self.peak = 0

    async def slow(self) -> str:
        self.running += 1
        self.peak = max(self.peak, self.running)
        await asyncio.sleep(0.01)
        self.running -= 1
        return "done"


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [1, 3])
async def test_no_more_than_the_limit_run_at_once(limit: int) -> None:
    tracker = Tracker()
    response = await async_dispatch(
        BATCH, {"slow": tracker.slow}, max_concurrency=limit
    )
    assert tracker.peak == limit
    assert [r["id"] for r in json.loads(response)] == list(range(1, 11))


@pytest.mark.asyncio
async def test_no_limit_by_default() -> None:
    tracker = Tracker()
    await async_dispatch(BATCH, {"slow": tracker.slow})
    assert tracker.peak == 10


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [0, -1, True, 1.5, "3"])
async def test_invalid_limit_raises(value: Any) -> None:
    with pytest.raises(ValueError, match="max_concurrency must be a positive int"):
        await async_dispatch(BATCH, {}, max_concurrency=value)
