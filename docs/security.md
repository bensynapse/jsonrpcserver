---
description: What to set before you expose a jsonrpcserver server to the internet. Exception messages, batch and body size limits, client-controlled parameters, the methods you expose, and a fix for 5.0.9.
---

# Security

jsonrpcserver handles requests from clients you may not trust. These are the
things to know before you put a server on the internet.

## If you are on 5.0.9

!!! danger "5.0.9 sends exception messages to the client"
    These docs describe 5.0.10, which isn't on PyPI yet.
    `pip install jsonrpcserver` gives you 5.0.9. In 5.0.9, when a method
    raises an exception it doesn't catch, the client gets the exception's
    message in `error.data`. Messages from database drivers and HTTP clients
    often contain connection strings, passwords, hostnames, file paths or SQL.

    Check your version with `pip show jsonrpcserver`.

Until you can upgrade, wrap each method so that it catches unexpected
exceptions itself, logs them and returns a plain Internal error:

```python
import functools
import logging
from typing import Any, Callable

from jsonrpcserver import Error, JsonRpcError, Result, Success, dispatch, method

logger = logging.getLogger(__name__)


def no_leak(func: Callable[..., Result]) -> Callable[..., Result]:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Result:
        try:
            return func(*args, **kwargs)
        except JsonRpcError:
            raise  # Errors you raise on purpose still reach the client.
        except Exception:
            logger.exception("Method %s failed", func.__name__)
            return Error(-32603, "Internal error")

    return wrapper


@method
@no_leak
def get_user(user_id: int) -> Result:
    raise ConnectionError("could not connect to postgres://admin:hunter2@db")
```

```pycon
>>> logging.disable(logging.CRITICAL)  # Keep the logged traceback out of this page.
>>> dispatch('{"jsonrpc": "2.0", "method": "get_user", "params": [1], "id": 1}')
'{"jsonrpc": "2.0", "error": {"code": -32603, "message": "Internal error"}, "id": 1}'
>>> logging.disable(logging.NOTSET)
```

Put `@no_leak` under `@method`, on every method. `functools.wraps` keeps the
function's signature, so jsonrpcserver still checks the params against it. For
async methods, write the same wrapper with `async def` and `await`.

The wrapper can't cover one case. An exception inside jsonrpcserver itself,
outside your method, still sends its message in a -32000 "Server error". That needs a bug in jsonrpcserver or in a custom
`validator`, so it's rare. Upgrade to 5.0.10 when it's out, and then remove
the wrapper.

5.0.9 also lacks `max_batch_size`, so limit the request body size in your web
server (see below). It sends `NaN` and `Infinity` in responses, which strict
JSON parsers reject. And when a result can't be serialized, such as a
`datetime`, `dispatch` raises `TypeError` instead of sending an error, so your
framework answers with its own error page.

## Exception messages stay on the server

From 5.0.10, if a method raises an exception it doesn't catch, the client
gets a -32603 "Internal error" with no `data`. The exception and its
traceback are logged, on the `jsonrpcserver` logger. Make sure your logging
configuration keeps them. [Errors and logging](errors.md#logging) lists the
loggers.

`debug=True` puts the message back in the response. Use it only in
development.

Errors you return on purpose with `Error`, `InvalidParams` or `JsonRpcError`
are sent as they are, so don't put secrets in their `data` either.

## What does reach the client

Some error responses always carry details, `debug` or not:

- **-32700 Parse error** carries the deserializer's exception message. With
  the default `json.loads`, that's harmless. A custom `deserializer` must not
  put secrets in its exception messages.
- **-32602 Invalid params** carries Python's explanation of why the params
  don't fit, which names your parameters, such as
  `got an unexpected keyword argument 'skip_checks'`. A client can use it to
  discover parameter names.
- **-32601 Method not found** repeats the method name the client sent.

[Errors and logging](errors.md) lists every error.

## Limit batch size

A single request can be a batch of thousands of requests. Each one is
validated and run. With `async_dispatch`, they all run at once. In one test,
on a laptop with Python 3.13, a 5 MB batch of 100,000 pings took about 4
seconds of CPU time. If the methods do I/O, a batch also multiplies the load
on your database or the APIs you call.

Set `max_batch_size` on every dispatch call:

```python
response = dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}', max_batch_size=100)
```

A bigger batch gets a single error response, and none of it runs. See
[Notifications and batches](batches.md#limit-the-batch-size). It's new in
5.0.10.

## Limit the request body

Also limit the size of the request body, in your web server or framework.
It stops a huge request before it's read into memory and parsed, which
`max_batch_size` can't do. Each [framework example](examples.md) sets a limit
of 1,000,000 bytes and names the setting it uses. Some frameworks have no
limit by default, and others allow 100 MB.

## Every parameter is up to the client

The client chooses the arguments, positional or named, for every parameter
your method has. That includes keyword-only parameters and ones with default
values. So this is unsafe:

```python
@method
def transfer(amount: int, *, skip_checks: bool = False) -> Result:
    ...
    return Success()
```

A client can send `{"amount": 100, "skip_checks": true}`. Keep server-side
options out of a method's signature. Pass them through
[`context`](context.md), which the client can't set, or use a separate
function.

The values themselves are whatever the JSON held. jsonrpcserver doesn't check
them against your type hints, so check them in the method.

## Only expose the methods you mean to

`@method` adds functions to one dict for the whole process. Any module you
import that uses `@method` adds methods to it, and they can all be called
through `dispatch` unless you pass `methods`. A later `@method` with the same
name replaces the earlier one without a warning.

For a public server, consider passing an explicit dict:

```python
def ping() -> Result:
    return Success("pong")


METHODS = {"ping": ping}

response = dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}', METHODS)
```

## The built-in server is for development

`serve()` is a small server built on Python's `http.server`. It has no TLS,
no authentication and no request size limit, and it doesn't set
`max_batch_size`. Use it to try things out, and put `dispatch` behind a real
web server or framework in production. The [examples](examples.md) show how.

By default, `serve()` listens on every network interface, so anyone who can
reach your machine can call your methods. Pass `"localhost"` to accept only
local connections, as in `serve("localhost", 8000)`. From 5.0.10 it says where
it's listening when it starts, including a note when that's every interface.

## Strict JSON

Python's `json` module accepts `NaN`, `Infinity` and numbers like `1e400` in a
request, which aren't valid JSON. [Validation](validation.md#nan-infinity-and-huge-numbers)
shows a stricter `deserializer` that rejects them. From 5.0.10, `dispatch`
and `async_dispatch` never write them with the default serializer: they send
an Internal error instead. `dispatch_to_serializable` gives you the float as
it is, so if your framework serializes the dict, check how it treats them.

## Reporting a vulnerability

Please report security problems privately, through the
[Security tab](https://github.com/bensynapse/jsonrpcserver/security) on GitHub.
See the [security policy](security-policy.md).
