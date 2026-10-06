# Security

jsonrpcserver handles requests from clients you may not trust. These are the
things to know before you put a server on the internet.

## Exception messages stay on the server

If a method raises an exception it doesn't catch, the client gets a -32603
"Internal error" with no `data`. The exception and its traceback are logged
through the `jsonrpcserver.dispatcher` logger (`jsonrpcserver.async_dispatcher`
for `async_dispatch`), so make sure your logging configuration keeps them.

Before 5.0.10, the exception message was sent to the client. Messages from
database drivers and HTTP clients often contain connection strings, passwords,
hostnames, file paths or SQL. Upgrade if you're on an older version.

`debug=True` puts the message back in the response. Use it only in
development.

Errors you return on purpose with `Error`, `InvalidParams` or `JsonRpcError`
are sent as they are, so don't put secrets in their `data` either.

## Limit batch size

A single request can be a batch of thousands of requests. Each one is
validated and run. With `async_dispatch`, they all run at once. A 5 MB batch of
100,000 pings took about 4 seconds of CPU time in one test. If the methods do
I/O, a batch also multiplies the load on your database or the APIs you call.

Set `max_batch_size` on every dispatch call:

```python
from jsonrpcserver import dispatch

response = dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}', max_batch_size=100)
```

Also limit the size of the request body in your web server or framework.

## Every parameter is up to the client

The client chooses the arguments, positional or named, for every parameter
your method has. That includes keyword-only parameters and ones with default
values. So this is unsafe:

```python
from jsonrpcserver import Result, Success, method


@method
def transfer(amount: int, *, skip_checks: bool = False) -> Result:
    ...
    return Success()
```

A client can send `{"amount": 100, "skip_checks": true}`. Keep server-side
options out of a method's signature. Pass them through `context`, which the
client can't set, or use a separate function.

The values themselves are whatever the JSON held. jsonrpcserver doesn't check
them against your type hints, so check them in the method.

## Only expose the methods you mean to

`@method` adds functions to one dict for the whole process. Any module you
import that uses `@method` adds methods to it, and they can all be called
through `dispatch` unless you pass `methods`. A later `@method` with the same
name replaces the earlier one without a warning.

For a public server, consider passing an explicit dict:

```python
from jsonrpcserver import Result, Success, dispatch


def ping() -> Result:
    return Success("pong")


METHODS = {"ping": ping}

response = dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}', METHODS)
```

## The built-in server is for development

`serve()` is a small server built on Python's `http.server`. It has no TLS,
no authentication and no request size limit. Use it to try things out, and put
`dispatch` behind a real web server or framework in production. The
[examples](examples.md) show how.

## NaN and Infinity

Python's `json` module accepts `NaN`, `Infinity` and numbers like `1e400` in a
request, which aren't valid JSON. To reject them, pass a stricter
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


def strict_loads(request: str):
    return json.loads(request, parse_constant=reject, parse_float=finite_float)
```

```python
>>> dispatch('{"jsonrpc": "2.0", "method": "ping", "params": [NaN], "id": 1}', METHODS, deserializer=strict_loads)
'{"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error", "data": "NaN is not valid JSON"}, "id": null}'
```

Responses never contain them. The default serializer refuses to write them.

## Reporting a vulnerability

Please report security problems privately, through the
[Security tab](https://github.com/bensynapse/jsonrpcserver/security) on GitHub.
See [SECURITY.md](https://github.com/bensynapse/jsonrpcserver/blob/main/SECURITY.md).
