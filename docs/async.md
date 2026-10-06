---
description: Use jsonrpcserver in asyncio servers with async_dispatch. Async and plain methods, concurrent batches, notifications, and the async versions of every dispatch function.
---

# Async

For asyncio servers, use `async_dispatch`. Methods can be `async`, and their
`await`s don't block the server.

```python
import asyncio

from jsonrpcserver import Result, Success, async_dispatch, method


@method
async def ping() -> Result:
    return Success("pong")
```

```pycon
>>> asyncio.run(async_dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}'))
'{"jsonrpc": "2.0", "result": "pong", "id": 1}'
```

In a real server you're already inside a coroutine, so write
`response = await async_dispatch(request)`.

`async_dispatch` takes the same options as [`dispatch`](dispatch.md).
`async_dispatch_to_serializable` and `async_dispatch_to_response` are the async
versions of the other two functions.

## Plain methods

Plain functions work as methods too:

```python
@method
def add(a: int, b: int) -> Result:
    return Success(a + b)
```

```pycon
>>> asyncio.run(
...     async_dispatch('{"jsonrpc": "2.0", "method": "add", "params": [2, 3], "id": 1}')
... )
'{"jsonrpc": "2.0", "result": 5, "id": 1}'
```

They run on the event loop, so a slow one holds up every other request. Make
slow methods `async`, or move the work to a thread with
`await asyncio.to_thread(...)`.

!!! info "New in 5.0.10"
    In 5.0.9, a plain method called through `async_dispatch` gives an
    Internal error. There, make every method `async def`.

It doesn't work the other way round. Async methods don't work with the
synchronous `dispatch`. The client gets an Internal error, and the log says to
use `async_dispatch`.

## Batches run concurrently

The requests in a batch run at the same time. These ten requests take about a
tenth of a second, not one second:

```python
import json
import time


@method
async def wait() -> Result:
    await asyncio.sleep(0.1)
    return Success()


batch = json.dumps([{"jsonrpc": "2.0", "method": "wait", "id": n} for n in range(10)])
```

```pycon
>>> start = time.monotonic()
>>> responses = json.loads(asyncio.run(async_dispatch(batch)))
>>> len(responses)
10
>>> time.monotonic() - start < 0.5
True
```

The responses still come back in the same order as the requests.

Every request in a batch runs at once, so a big batch can start thousands of
tasks. Set `max_batch_size` if clients can send big batches. See
[Security](security.md#limit-batch-size).

## Notifications

A notification is a request with no `id`. The spec says not to respond to it,
so `async_dispatch` gives an empty string:

```pycon
>>> asyncio.run(async_dispatch('{"jsonrpc": "2.0", "method": "ping"}'))
''
```

With HTTP you have to send something, so send an empty body with status 204.
With websockets or a message queue, you can skip sending:

```python
from typing import Awaitable, Callable


async def handle(request: str, send: Callable[[str], Awaitable[None]]) -> None:
    if response := await async_dispatch(request):
        await send(response)
```

The [framework examples](examples.md) include aiohttp, FastAPI, Sanic,
Tornado, websockets and ZeroMQ's asyncio API.
