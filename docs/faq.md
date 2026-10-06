---
description: Answers to common jsonrpcserver questions. Internal errors with no details, tracebacks, HTTP status codes, printing responses, threads, orjson and the old domains.
---

# FAQ

## My method works, but the client gets "Internal error" with no details

Either the method raised an exception, or it returned something other than
`Success(...)` or `Error(...)`. The most common case is a method written for
4.x that returns its result directly, such as `return "pong"`. Return
`Success("pong")` instead. See [Migration](migration.md).

The details are in your server's log, not in the response. From 5.0.10 that's
on purpose, so that exception messages don't leak to clients. If the log
shows nothing, see the next question.

## How do I see the traceback?

jsonrpcserver logs it on the `jsonrpcserver` logger, but doesn't configure
logging. Configure it when your server starts:

```python
import logging

logging.basicConfig(level=logging.INFO)
```

While developing, you can also pass `debug=True` to `dispatch` to get the
exception message in the response. See [Errors and logging](errors.md).

## Which HTTP status code should I send?

```python
def status(response: str) -> int:
    return 200 if response else 204
```

A JSON-RPC error is still a successful HTTP exchange, so send 200 with it. If
`dispatch` gives an empty string, the request was a notification and there's
no body, so send 204 No Content. The built-in `serve()` does this from
5.0.10.

## Why does printing the result of dispatch_to_response fail?

`print(dispatch_to_response(...))` raises `TypeError: not all arguments
converted during string formatting`. That's a bug in oslash, the library the
`Response` objects come from. Print `to_dict(response)` instead, or use
`dispatch_to_serializable`, which gives dicts. See
[Dispatch](dispatch.md#dispatch_to_response).

## How do I get the response as a dict instead of a string?

Use `dispatch_to_serializable`. See
[other return types](dispatch.md#other-return-types).

## How do I rename a method?

Use `@method(name="new_name")`, or pass your own dict as the
[methods](dispatch.md#methods) argument.

## Can a method get the HTTP request, user or database connection?

Pass it as `context`. It becomes the first argument of every method, and the
client can't change it. [Context](context.md) has examples for Flask, FastAPI
and Django.

## Why does my async method give an Internal error?

You called it with `dispatch`. Async methods need
[`async_dispatch`](async.md).

## Is it thread-safe?

Yes, including on free-threaded Python. Register your methods at import time.
See [Threads](threads.md).

## How do I turn off request validation?

Pass `validator=lambda _: None`. It saves time, but bad requests then get odd
answers. See [Validation](validation.md#turning-it-off).

## Can I use orjson or ujson?

Yes, through `deserializer` and `serializer`. ujson's functions fit as they
are. [orjson](https://pypi.org/project/orjson/)'s `dumps` returns bytes, and
`dispatch` must return a string, so decode it:

<!-- requires: orjson -->
```python
import orjson

from jsonrpcserver import Result, Success, dispatch


def ping() -> Result:
    return Success("pong")


def orjson_dumps(response: object) -> str:
    return orjson.dumps(response).decode()


print(
    dispatch(
        '{"jsonrpc": "2.0", "method": "ping", "id": 1}',
        {"ping": ping},
        deserializer=orjson.loads,
        serializer=orjson_dumps,
    )
)
```

```text title="Output"
{"jsonrpc":"2.0","result":"pong","id":1}
```

orjson writes `NaN` and `Infinity` as `null` instead of raising, so a result
that contains them is sent with `null` in their place, not as an error.

## Where did the examples on the wiki go?

They're on the [Frameworks](examples.md) pages now, and CI runs each one
against a real server.

## Where is the old documentation website?

The project's old domains, jsonrpcserver.com and jsonrpcclient.com, now
belong to someone else. Ignore them and any links to them. The copy at
explodinglabs.com/jsonrpcserver/ is old and no longer updated, and so is the
one on Read the Docs.

The official places are these docs, the [GitHub
repository](https://github.com/bensynapse/jsonrpcserver) and the [PyPI
project](https://pypi.org/project/jsonrpcserver/).
