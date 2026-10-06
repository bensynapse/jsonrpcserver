---
description: How jsonrpcserver validates JSON-RPC requests. What the default schema checks, custom validators, what you lose by turning it off, and rejecting NaN.
---

# Validation

After parsing a request, jsonrpcserver checks it against the JSON-RPC spec.
A request that fails gets a -32600 "Invalid request" response, and no method
runs.

## What the default checks

The default validator checks each request against a JSON schema. A request
must be an object with:

- `"jsonrpc": "2.0"`, exactly
- a `method` that's a string
- `params`, if present, that's an array or an object
- an `id`, if present, that's a string, a number or null

Nothing else is allowed in the object.

```python
from jsonrpcserver import Result, Success, dispatch, method


@method
def ping() -> Result:
    return Success("pong")
```

```pycon
>>> dispatch('{"jsonrpc": "2.0", "method": "ping", "params": "x", "id": 1}')
'{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid request", "data": "The request failed schema validation"}, "id": null}'
```

The error doesn't say which rule the request broke, and its `id` is null
because the request couldn't be trusted.

## A custom validator

Pass `validator` to use your own. It gets the parsed request, a dict, and
should raise an exception of any kind if the request is invalid. What it
returns is ignored. In a batch, it's called once for each request.

This one runs the default checks, then refuses requests without an `id`, so
clients can't send notifications:

```python
from typing import Any, Dict

from jsonrpcserver.main import default_validator


def no_notifications(request: Dict[str, Any]) -> None:
    default_validator(request)
    if "id" not in request:
        raise ValueError("Notifications aren't allowed")
```

```pycon
>>> dispatch('{"jsonrpc": "2.0", "method": "ping"}', validator=no_notifications)
'{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid request", "data": "The request failed schema validation"}, "id": null}'
```

The exception's message isn't sent to the client.

!!! info "Changed in 5.0.10"
    Before 5.0.10, a batch was validated as a whole: the validator was called
    once, with the list. A validator that enforced a rule about the whole
    batch, such as refusing batches, no longer sees the list. Use
    `max_batch_size` for a size limit.

## Turning it off

Validation takes most of the time `dispatch` spends on a small method. If
your own code makes the requests, so you know they're valid, you can turn it
off:

```pycon
>>> dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}', validator=lambda _: None)
'{"jsonrpc": "2.0", "result": "pong", "id": 1}'
```

Without it, `dispatch` still never raises, but bad requests get odd answers:

```pycon
>>> import logging
>>> logging.disable(logging.CRITICAL)  # Keep the logged traceback out of this page.
>>> no_validation = lambda _: None
>>> dispatch('{"method": "ping", "id": 1}', validator=no_validation)
'{"jsonrpc": "2.0", "result": "pong", "id": 1}'
>>> dispatch(
...     '{"jsonrpc": "2.0", "method": "ping", "params": "x", "id": 1}',
...     validator=no_validation,
... )
'{"jsonrpc": "2.0", "result": "pong", "id": 1}'
>>> dispatch('{"jsonrpc": "2.0", "id": 1}', validator=no_validation)
'{"jsonrpc": "2.0", "error": {"code": -32000, "message": "Server error"}, "id": null}'
>>> logging.disable(logging.NOTSET)
```

A request with no `jsonrpc` member runs, and params that aren't a list or an
object are ignored. A request with no `method` gets a -32000 "Server error",
and jsonrpcserver logs it as an error of its own. Keep validation on for
anything that strangers can reach.

## NaN, Infinity and huge numbers

Python's `json` module accepts `NaN`, `Infinity` and numbers like `1e400` in
a request. They aren't valid JSON, and the schema can't see them, because
they're already floats by the time it runs. To reject them, pass a stricter
`deserializer`:

```python
import json
import math


def reject(constant: str) -> None:
    raise ValueError(f"{constant} is not valid JSON")


def finite_float(text: str) -> float:
    number = float(text)
    if math.isinf(number):
        raise ValueError(f"{text} is too big")
    return number


def strict_loads(request: str) -> Any:
    return json.loads(request, parse_constant=reject, parse_float=finite_float)
```

```pycon
>>> dispatch(
...     '{"jsonrpc": "2.0", "method": "ping", "params": [NaN], "id": 1}',
...     deserializer=strict_loads,
... )
'{"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error", "data": "NaN is not valid JSON"}, "id": null}'
```

Responses never contain them in 5.0.10: the default serializer refuses to
write them and sends an Internal error instead. 5.0.9 writes them as they
are.
