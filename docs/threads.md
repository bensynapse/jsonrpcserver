---
description: jsonrpcserver's dispatch functions are safe to call from several threads, including on free-threaded Python 3.14t. Register methods at import time.
---

# Threads

`dispatch` and the other dispatch functions can be called from several
threads at once, so they work with threaded servers such as Flask's, Django's
and `serve()`. That includes free-threaded Python (3.14t), where there is no
GIL. The test suite runs on 3.14t. It calls `dispatch` from many threads at
once, with single requests, batches and a different context in each thread,
and checks that every response is right.

```python
from concurrent.futures import ThreadPoolExecutor

from jsonrpcserver import Result, Success, dispatch, method


@method
def square(number: int) -> Result:
    return Success(number * number)


def call(number: int) -> str:
    return dispatch(
        f'{{"jsonrpc": "2.0", "method": "square", "params": [{number}], "id": {number}}}'
    )


with ThreadPoolExecutor(max_workers=8) as pool:
    responses = list(pool.map(call, range(100)))

print(responses[9])
```

```text title="Output"
{"jsonrpc": "2.0", "result": 81, "id": 9}
```

`dispatch` keeps no state of its own between calls. Each call only reads the
methods dict.

## Register methods at import time

`@method` writes to one dict for the whole process. Run all your `@method`
decorators when your modules are imported, before the server starts handling
requests, which is what happens when they decorate top-level functions. Don't
add or replace methods while other threads are dispatching. If the set of
methods has to change at run time, pass a `methods` dict. To change it, build
a new dict and pass that from then on.

## Your methods

jsonrpcserver doesn't make your methods thread-safe. If a method changes
shared state, protect it with a lock as you would anywhere else. Objects
passed as `context` are shared too, if you pass the same one to every call.

## asyncio

`async_dispatch` runs on one event loop, and the requests in a batch run
concurrently on it. See [Async](async.md). Don't share one event loop's
objects between threads.
