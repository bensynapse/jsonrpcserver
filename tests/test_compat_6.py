"""Code that only uses @method, Success, Error, InvalidParams and dispatch runs
unchanged from 5.x to 6.0 (plans/6.0.md, acceptance)."""

import json

from jsonrpcserver import Error, InvalidParams, Result, Success, dispatch, method


def test_5x_style_methods_work_unchanged() -> None:
    @method(name="compat_add")
    def add(a: int, b: int) -> Result:
        return Success(a + b)

    @method(name="compat_fail")
    def fail() -> Result:
        return Error(1, "It failed", {"why": "example"})

    @method(name="compat_rate")
    def rate(stars: int) -> Result:
        if stars not in range(1, 6):
            return InvalidParams("Stars must be 1 to 5")
        return Success()

    batch = [
        {"jsonrpc": "2.0", "method": "compat_add", "params": [2, 3], "id": 1},
        {"jsonrpc": "2.0", "method": "compat_fail", "id": 2},
        {"jsonrpc": "2.0", "method": "compat_rate", "params": [9], "id": 3},
        {"jsonrpc": "2.0", "method": "compat_rate", "params": [5], "id": 4},
    ]
    assert json.loads(dispatch(json.dumps(batch))) == [
        {"jsonrpc": "2.0", "result": 5, "id": 1},
        {
            "jsonrpc": "2.0",
            "error": {"code": 1, "message": "It failed", "data": {"why": "example"}},
            "id": 2,
        },
        {
            "jsonrpc": "2.0",
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": "Stars must be 1 to 5",
            },
            "id": 3,
        },
        {"jsonrpc": "2.0", "result": None, "id": 4},
    ]
