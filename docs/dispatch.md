---
description: The dispatch function in jsonrpcserver and every option it takes, from methods and context to debug, max_batch_size, deserializer, serializer and validator. Plus the dict and Response forms of the result.
---

# Dispatch

`dispatch` takes a JSON-RPC request string, calls the method and gives a
JSON-RPC response string.

```python
from jsonrpcserver import Result, Success, dispatch, method


@method
def ping() -> Result:
    return Success("pong")
```

```pycon
>>> dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}')
'{"jsonrpc": "2.0", "result": "pong", "id": 1}'
```

It never raises for a bad request or a failing method. Those become JSON-RPC
error responses, as the spec requires:

```pycon
>>> dispatch('{"jsonrpc": "2.0", "method": "nope", "id": 1}')
'{"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found", "data": "nope"}, "id": 1}'
>>> dispatch("{")
'{"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error", "data": "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"}, "id": null}'
```

[Errors and logging](errors.md) lists every error it can send.

A notification, or a batch of only notifications, gives an empty string. The
spec says not to respond to those. [Notifications and batches](batches.md)
covers both.

[See how dispatch is used in different frameworks.](examples.md)

## Options

All of these are keyword arguments, apart from `methods`, which can also be
the second positional argument.

### methods

The methods that requests can call, as a dict of names to functions. Use this
instead of the `@method` decorator:

```python
def multiply(a: int, b: int) -> Result:
    return Success(a * b)
```

```pycon
>>> dispatch(
...     '{"jsonrpc": "2.0", "method": "multiply", "params": [2, 3], "id": 1}',
...     methods={"multiply": multiply},
... )
'{"jsonrpc": "2.0", "result": 6, "id": 1}'
```

The default is the dict that `@method` fills in,
`jsonrpcserver.methods.global_methods`. Any mapping works, not only a dict.

### context

If given, it's passed as the first argument to every method. Use it for things
like the database connection or the logged-in user:

```python
def greet(context: str, name: str) -> Result:
    return Success(context + " " + name)
```

```pycon
>>> dispatch(
...     '{"jsonrpc": "2.0", "method": "greet", "params": ["Beau"], "id": 1}',
...     methods={"greet": greet},
...     context="Hello",
... )
'{"jsonrpc": "2.0", "result": "Hello Beau", "id": 1}'
```

The client can't see or set it. [Context](context.md) shows how to pass the
HTTP request or the user from Flask, FastAPI and Django.

### debug

When a method raises an exception it doesn't catch, the client gets a -32603
"Internal error" with no details, and the exception is logged. With
`debug=True`, the exception message goes into the response's `data` too:

```python
def broken() -> Result:
    raise ValueError("Something went wrong")
```

```pycon
>>> import logging
>>> logging.disable(logging.CRITICAL)  # Keep the logged traceback out of this page.
>>> dispatch('{"jsonrpc": "2.0", "method": "broken", "id": 1}', methods={"broken": broken})
'{"jsonrpc": "2.0", "error": {"code": -32603, "message": "Internal error"}, "id": 1}'
>>> dispatch(
...     '{"jsonrpc": "2.0", "method": "broken", "id": 1}',
...     methods={"broken": broken},
...     debug=True,
... )
'{"jsonrpc": "2.0", "error": {"code": -32603, "message": "Internal error", "data": "Something went wrong"}, "id": 1}'
>>> logging.disable(logging.NOTSET)
```

Only use it in development. Exception messages can include passwords, file
paths and SQL. The default is `False`.

!!! info "New in 5.0.10"
    The `debug` option, and leaving the message out by default. In 5.0.9 and
    earlier the message is always sent, and `debug` raises `TypeError`. See
    [Security](security.md#if-you-are-on-509).

### max_batch_size

The most requests a batch may hold. A bigger batch gets a single -32600
"Invalid request" response, and none of its requests are run:

```pycon
>>> dispatch(
...     '[{"jsonrpc": "2.0", "method": "ping", "id": 1}, {"jsonrpc": "2.0", "method": "ping", "id": 2}]',
...     max_batch_size=1,
... )
'{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid request", "data": "The batch has 2 requests. The limit is 1."}, "id": null}'
```

The default, `None`, means no limit. A server open to the internet should set
one. See [Security](security.md#limit-batch-size). Anything other than `None`
or a positive `int` raises `ValueError`.

!!! info "New in 5.0.10"
    5.0.9 raises `TypeError` for this keyword.

### deserializer

The function that parses the request string. The default is `json.loads`.

<!-- requires: ujson -->
```python
import ujson

dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}', deserializer=ujson.loads)
```

If it raises, the client gets a -32700 "Parse error" whose `data` is the
exception's message, so don't put anything secret in it.

### serializer

The function that turns the response into a string. The default is
`json.dumps` with `allow_nan=False`, so a result containing `NaN` or
`Infinity` gives an Internal error instead of output that isn't valid JSON.

If the serializer raises for a response (say the method returned a
`datetime`), that response becomes an Internal error, and the error is logged.
The rest of a batch is sent as usual.

<!-- requires: ujson -->
```python
dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}', serializer=ujson.dumps)
```

!!! info "Changed in 5.0.10"
    5.0.9 writes `NaN` and `Infinity` into the response, and raises when the
    serializer fails.

### validator

The function that checks each request against the JSON-RPC spec, after
parsing. The default checks against a JSON schema. [Validation](validation.md)
says what it checks, how to write your own, and what you lose by turning it
off.

!!! info "Changed in 5.0.10"
    In a batch, the validator is called once for each request. In 5.0.9 it
    was called once with the whole list.

## Other return types

`dispatch` is also called `dispatch_to_json`. Two other functions take the
same options, apart from `serializer`, and give the response in other forms.

### dispatch_to_serializable

It gives a dict, a list of dicts for a batch, or `None` for a notification.
Use it when your framework serializes the response itself:

```pycon
>>> from jsonrpcserver import dispatch_to_serializable
>>> dispatch_to_serializable('{"jsonrpc": "2.0", "method": "ping", "id": 1}')
{'jsonrpc': '2.0', 'result': 'pong', 'id': 1}
```

### dispatch_to_response

It gives `Response` objects, or `None` for a notification. Use it to look at
or change responses before they're serialized. It also takes a `post_process`
function, which is applied to each response.

A `Response` comes from the [oslash](https://pypi.org/project/oslash/)
library. It's a `Right` holding a `SuccessResponse`, or a `Left` holding an
`ErrorResponse`. oslash has no public way to read them, so check which one you
have and read `_value` or `_error`. Those attributes are stable for all of
5.x:

```pycon
>>> from oslash.either import Left
>>> from jsonrpcserver import dispatch_to_response
>>> response = dispatch_to_response('{"jsonrpc": "2.0", "method": "ping", "id": 1}')
>>> isinstance(response, Left)
False
>>> response._value
SuccessResponse(result='pong', id=1)
>>> error = dispatch_to_response('{"jsonrpc": "2.0", "method": "nope", "id": 1}')
>>> isinstance(error, Left)
True
>>> error._error
ErrorResponse(code=-32601, message='Method not found', data='nope', id=1)
```

`print(response)` raises `TypeError: not all arguments converted during
string formatting`, because of a bug in oslash. Turn it into a dict first with
`to_dict`:

```pycon
>>> from jsonrpcserver.response import to_dict
>>> print(to_dict(response))
{'jsonrpc': '2.0', 'result': 'pong', 'id': 1}
```

For a batch, it gives a list of Responses. Everything here works the same
with `async_dispatch_to_serializable` and `async_dispatch_to_response`. See
[Async](async.md).
