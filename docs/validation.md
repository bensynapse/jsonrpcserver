---
description: How jsonrpcserver validates JSON-RPC requests. What the default validator checks, custom validators, what you lose by turning it off, and rejecting NaN.
---

# Validation

After parsing a request, jsonrpcserver checks it against the JSON-RPC spec.
A request that fails gets a -32600 "Invalid request" response, and no method
runs.

## What the default checks

The default validator checks each request against the JSON-RPC 2.0 rules. A
request must be an object with:

- `"jsonrpc": "2.0"`, exactly
- a `method` that's a string
- `params`, if present, that's an array or an object
- an `id`, if present, that's a string, a number or null

Nothing else is allowed in the object.

!!! info "Changed in 6.0"
    5.x checked these rules with a JSON Schema and the jsonschema library.
    6.0 checks the same rules itself, which is faster and needs no
    dependency. A test compares the two on 500 generated requests and a list of
    edge cases.

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

Pass `validator` to use your own. It gets the parsed request, usually a
dict, and should raise an exception of any kind if the request is invalid.
It can also get anything else that parsed, such as a number, a string or an
empty list, so don't assume a dict. What it
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

Validation is cheap from 6.0: about 4% of the time `dispatch` spends on a
small method (0.4 of 9.6 microseconds, Python 3.13, measured 2026-11-06). In
5.x, with jsonschema, it was about 72%. If your own code makes the requests,
so you know they're valid, you can still turn it off:

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
and jsonrpcserver logs it as an error of its own. An empty batch, `[]`, gets
no response at all instead of an error. Keep validation on for anything that
strangers can reach.

## NaN, Infinity and huge numbers

`NaN`, `Infinity`, `-Infinity` and numbers too big for a float, like `1e400`,
aren't valid JSON. Python's `json` module accepts them anyway, and the
validator can't see them, because they're already floats by the time it runs.
So the default deserializer rejects them, and the client gets a Parse error:

```pycon
>>> dispatch('{"jsonrpc": "2.0", "method": "ping", "params": [NaN], "id": 1}')
'{"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error", "data": "NaN is not valid JSON"}, "id": null}'
```

To accept them, pass `deserializer=json.loads`. The default serializer never
writes them into a response: it refuses, and the client gets an Internal
error instead. `dispatch_to_serializable` returns the float itself, so if your
framework serializes the dict, check how it treats them.

!!! info "Changed in 6.0"
    5.x accepted them unless you passed a stricter `deserializer`.
