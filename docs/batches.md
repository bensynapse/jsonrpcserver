---
description: How jsonrpcserver handles JSON-RPC notifications and batches. When there's nothing to send, HTTP 204, response order, invalid members, empty batches and max_batch_size.
---

# Notifications and batches

## Notifications

A notification is a request with no `id`. The client doesn't want an answer,
and the spec says the server must not send one. The method still runs, and
`dispatch` gives an empty string:

```python
from jsonrpcserver import Result, Success, dispatch, method


@method
def ping() -> Result:
    return Success("pong")
```

```pycon
>>> dispatch('{"jsonrpc": "2.0", "method": "ping"}')
''
```

What to do with the empty string depends on the transport:

- **HTTP** always sends a response, so send status 204 No Content with no
  body.
- **websockets** and most message queues: send nothing.
- **ZeroMQ REQ/REP** sockets must answer every message, so send the empty
  string.

The [framework examples](examples.md) each do the right thing.

!!! note
    A notification gets no response even when it fails, so the client never
    hears about the error. That's how the spec wants it. If the method raises
    an exception, it's logged (see [Errors and logging](errors.md)). Other
    errors, such as an unknown method or params that don't fit, aren't
    recorded anywhere.

## Batches

A batch is a JSON array of requests. Each one is run, and the responses come
back as an array:

```pycon
>>> dispatch(
...     '[{"jsonrpc": "2.0", "method": "ping", "id": 1}, {"jsonrpc": "2.0", "method": "ping", "id": 2}]'
... )
'[{"jsonrpc": "2.0", "result": "pong", "id": 1}, {"jsonrpc": "2.0", "result": "pong", "id": 2}]'
```

jsonrpcserver sends the responses in the same order as the requests. The spec
doesn't require that, so clients should match responses to requests by `id`.

`dispatch` runs the requests one after another. `async_dispatch` runs them all
at once. See [Async](async.md#batches-run-concurrently).

### Notifications in a batch

Notifications in a batch run, but get no response. If every request in a
batch is a notification, there's nothing to send, and `dispatch` gives an
empty string:

```pycon
>>> dispatch(
...     '[{"jsonrpc": "2.0", "method": "ping", "id": 1}, {"jsonrpc": "2.0", "method": "ping"}]'
... )
'[{"jsonrpc": "2.0", "result": "pong", "id": 1}]'
>>> dispatch('[{"jsonrpc": "2.0", "method": "ping"}, {"jsonrpc": "2.0", "method": "ping"}]')
''
```

### Invalid members

Each request in a batch is checked on its own. One that isn't a valid request
gets its own -32600 "Invalid request" response, with `id` null, and the
others run as usual:

```pycon
>>> dispatch('[1, {"jsonrpc": "2.0", "method": "ping", "id": 1}]')
'[{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid request", "data": "The request failed schema validation"}, "id": null}, {"jsonrpc": "2.0", "result": "pong", "id": 1}]'
```

An array inside a batch is not a request either, so it gets the same error.

!!! info "Changed in 5.0.10"
    In 5.0.9, one invalid member got the whole batch rejected with a single
    "Invalid request" response.

### An empty batch

The spec says an empty array gets a single error response, not an empty
array:

```pycon
>>> dispatch("[]")
'{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid request", "data": "The request failed schema validation"}, "id": null}'
```

## Limit the batch size

A client can put thousands of requests in one batch, and each one is
validated and run. Set `max_batch_size` on every dispatch call on a server
that strangers can reach:

```pycon
>>> big_batch = (
...     "[" + ", ".join(['{"jsonrpc": "2.0", "method": "ping", "id": 1}'] * 101) + "]"
... )
>>> dispatch(big_batch, max_batch_size=100)
'{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid request", "data": "The batch has 101 requests. The limit is 100."}, "id": null}'
```

A batch over the limit gets one error response, and none of its requests run.
A single request that isn't in a batch is never affected. The default,
`None`, means no limit.

`max_batch_size` must be `None` or a positive `int`. Anything else, including
`0`, `True`, `1.5` or `"100"`, raises `ValueError` when you call `dispatch`:

```pycon
>>> dispatch(big_batch, max_batch_size=0)
Traceback (most recent call last):
    ...
ValueError: max_batch_size must be a positive int or None, not 0
```

!!! info "New in 5.0.10"
    `max_batch_size`. On 5.0.9, limit the size of the request body in your
    web server instead. [Security](security.md#limit-batch-size) explains
    why both matter.
