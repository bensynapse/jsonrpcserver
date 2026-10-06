# FAQ

## How do I turn off request validation?

Validating each request against the JSON-RPC schema takes about three
quarters of the dispatch time for a trivial method. If you know the requests
are valid, for example because your own code makes them, turn it off:

```python
from jsonrpcserver import Result, Success, dispatch, method


@method
def ping() -> Result:
    return Success("pong")


dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}', validator=lambda _: None)
```

Without validation, a malformed request can give a less helpful error, but
`dispatch` still won't raise.

## Which HTTP status code should I send?

```python
def status(response: str) -> int:
    return 200 if response else 204
```

A JSON-RPC error is still a successful HTTP exchange, so send 200 with it. If
`dispatch` gives an empty string, the request was a notification and there's
no body, so send 204 No Content. The built-in `serve()` does this.

## How do I rename a method?

Use `@method(name="new_name")`, or pass your own dict as the
[methods](dispatch.md#methods) argument.

## Can a method get the HTTP request, user or database connection?

Pass it as [context](dispatch.md#context). It becomes the first argument of
every method, and the client can't change it.

## How do I get the response as a dict instead of a string?

Use `dispatch_to_serializable`. See
[other return types](dispatch.md#other-return-types).

## Why does my async method give an Internal error?

You called it with `dispatch`. Async methods need
[`async_dispatch`](async.md).

## Where did the examples on the wiki go?

They're on the [Examples](examples.md) page now, and CI runs each one against
a real server.
