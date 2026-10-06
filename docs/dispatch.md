# Dispatch

`dispatch` takes a JSON-RPC request string, calls the method and gives a
JSON-RPC response string.

```python
from jsonrpcserver import Result, Success, dispatch, method


@method
def ping() -> Result:
    return Success("pong")
```

```python
>>> dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}')
'{"jsonrpc": "2.0", "result": "pong", "id": 1}'
```

It never raises for a bad request or a failing method. Those become JSON-RPC
error responses, as the spec requires:

```python
>>> dispatch('{"jsonrpc": "2.0", "method": "nope", "id": 1}')
'{"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found", "data": "nope"}, "id": 1}'
>>> dispatch("{")
'{"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error", "data": "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"}, "id": null}'
```

A batch gets a list of responses, in the same order:

```python
>>> dispatch('[{"jsonrpc": "2.0", "method": "ping", "id": 1}, {"jsonrpc": "2.0", "method": "ping", "id": 2}]')
'[{"jsonrpc": "2.0", "result": "pong", "id": 1}, {"jsonrpc": "2.0", "result": "pong", "id": 2}]'
```

A notification, or a batch of only notifications, gives an empty string. The
spec says not to respond to those.

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

```python
>>> dispatch('{"jsonrpc": "2.0", "method": "multiply", "params": [2, 3], "id": 1}', methods={"multiply": multiply})
'{"jsonrpc": "2.0", "result": 6, "id": 1}'
```

The default is the dict that `@method` fills in.

### context

If given, it's passed as the first argument to every method. Use it for things
like the database connection or the logged-in user:

```python
def greet(context: str, name: str) -> Result:
    return Success(context + " " + name)
```

```python
>>> dispatch('{"jsonrpc": "2.0", "method": "greet", "params": ["Beau"], "id": 1}', methods={"greet": greet}, context="Hello")
'{"jsonrpc": "2.0", "result": "Hello Beau", "id": 1}'
```

The client can't see or set it.

### debug

When a method raises an exception it doesn't catch, the client gets a -32603
"Internal error" with no details, and the exception is logged. With
`debug=True`, the exception message goes into the response's `data` too:

```python
def broken() -> Result:
    raise ValueError("Something went wrong")
```

```python
>>> import logging
>>> logging.disable(logging.CRITICAL)  # Keep the logged traceback out of this page.
>>> dispatch('{"jsonrpc": "2.0", "method": "broken", "id": 1}', methods={"broken": broken})
'{"jsonrpc": "2.0", "error": {"code": -32603, "message": "Internal error"}, "id": 1}'
>>> dispatch('{"jsonrpc": "2.0", "method": "broken", "id": 1}', methods={"broken": broken}, debug=True)
'{"jsonrpc": "2.0", "error": {"code": -32603, "message": "Internal error", "data": "Something went wrong"}, "id": 1}'
>>> logging.disable(logging.NOTSET)
```

Only use it in development. Exception messages can include passwords, file
paths and SQL. The default is `False`.

### max_batch_size

The most requests a batch may hold. A bigger batch gets a single -32600
"Invalid request" response, and none of its requests are run:

```python
>>> dispatch('[{"jsonrpc": "2.0", "method": "ping", "id": 1}, {"jsonrpc": "2.0", "method": "ping", "id": 2}]', max_batch_size=1)
'{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid request", "data": "The batch has 2 requests. The limit is 1."}, "id": null}'
```

The default, `None`, means no limit. A server open to the internet should set
one. See [Security](security.md).

### deserializer

The function that parses the request string. The default is `json.loads`.

<!-- requires: ujson -->
```python
import ujson

dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}', deserializer=ujson.loads)
```

### serializer

The function that turns the response into a string. The default is
`json.dumps` with `allow_nan=False`, so a result containing `NaN` or
`Infinity` gives an Internal error instead of output that isn't valid JSON.

If the serializer raises for a response (say the method returned a
`datetime`), that response becomes an Internal error. The rest of a batch is
sent as usual.

<!-- requires: ujson -->
```python
dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}', serializer=ujson.dumps)
```

### validator

The function that checks each request against the JSON-RPC spec, after
parsing. It should raise an exception, any exception, if the request is
invalid. In a batch, it's called once for each request. The default checks
against a JSON schema.

Validation takes most of the time for a small method. If you're sure the
requests are valid, turn it off:

```python
dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}', validator=lambda _: None)
```

## Other return types

`dispatch` is an alias for `dispatch_to_json`. Two other functions take the
same options, apart from `serializer`, and give the response in other forms:

- `dispatch_to_serializable` gives a dict, a list of dicts for a batch, or
  `None` for a notification.
- `dispatch_to_response` gives `Response` objects. Each is an oslash `Right`
  holding a `SuccessResponse`, or a `Left` holding an `ErrorResponse`. Both are
  defined in
  [`jsonrpcserver.response`](https://github.com/bensynapse/jsonrpcserver/blob/main/jsonrpcserver/response.py).

```python
>>> from jsonrpcserver import dispatch_to_serializable
>>> dispatch_to_serializable('{"jsonrpc": "2.0", "method": "ping", "id": 1}')
{'jsonrpc': '2.0', 'result': 'pong', 'id': 1}
```
