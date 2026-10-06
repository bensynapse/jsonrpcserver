---
description: How to unit test jsonrpcserver methods. Call them directly, test them through dispatch with your own methods dict, and keep the global methods from leaking between tests.
---

# Testing

## Call the method directly

`@method` returns your function unchanged, so a test can call it like any
other function and compare the result:

```python
from jsonrpcserver import Error, Result, Success, method


@method
def divide(a: float, b: float) -> Result:
    if b == 0:
        return Error(1, "Can't divide by zero")
    return Success(a / b)


def test_divide() -> None:
    assert divide(6, 3) == Success(2)
    assert divide(1, 0) == Error(1, "Can't divide by zero")


test_divide()
```

`Success` and `Error` results compare equal when they hold the same values.

## Test through dispatch

To test what the client sees, including the JSON-RPC parts and the parameter
check, call `dispatch_to_serializable` with a dict of methods. It gives a dict,
which is easier to compare than a string:

```python
from jsonrpcserver import dispatch_to_serializable


def test_divide_request() -> None:
    response = dispatch_to_serializable(
        '{"jsonrpc": "2.0", "method": "divide", "params": [1, 0], "id": 1}',
        {"divide": divide},
    )
    assert response == {
        "jsonrpc": "2.0",
        "error": {"code": 1, "message": "Can't divide by zero"},
        "id": 1,
    }


def test_divide_wrong_params() -> None:
    response = dispatch_to_serializable(
        '{"jsonrpc": "2.0", "method": "divide", "params": [1], "id": 1}',
        {"divide": divide},
    )
    assert response is not None
    assert response["error"]["code"] == -32602


test_divide_request()
test_divide_wrong_params()
```

Passing the dict keeps the test to the methods you meant. Without it,
`dispatch` uses every method registered with `@method` anywhere in the test
process.

## The global methods

`@method` adds to one dict for the whole process,
`jsonrpcserver.methods.global_methods`. In a test suite, every test module
that's imported adds to it. A later `@method` with the same name replaces an
earlier one without a warning. If two test modules define a method called
`ping`, whichever is imported last wins.

Either pass `methods` explicitly in tests, as above, or give test methods
unique names. To start a test with no registered methods, clear the dict and
put it back afterwards. With pytest:

```python
from typing import Any, Dict, Iterator

from jsonrpcserver.methods import global_methods


def clean_methods() -> Iterator[Dict[str, Any]]:  # Decorate with @pytest.fixture.
    saved = dict(global_methods)
    global_methods.clear()
    yield global_methods
    global_methods.clear()
    global_methods.update(saved)
```

## Async methods

An async method is a coroutine function, so run it with `asyncio.run` or
pytest-asyncio's `@pytest.mark.asyncio`:

```python
import asyncio


async def ping() -> Result:
    return Success("pong")


assert asyncio.run(ping()) == Success("pong")
```

## Logged errors

An exception that a method doesn't catch is logged, and the client gets a
bare Internal error. To check that in a test, use pytest's `caplog` fixture
and look for a record from the `jsonrpcserver.dispatcher` logger. See
[Errors and logging](errors.md#logging).
