---
description: Every error code jsonrpcserver sends, what its data holds, what reaches the client and what is logged. The jsonrpcserver loggers, debug mode, and how to see tracebacks.
---

# Errors and logging

## The errors the client can get

These are the errors jsonrpcserver sends by itself. Your own errors, from
`Error` or `JsonRpcError`, are sent exactly as you made them.

| Code | Message | When | `data` |
|---|---|---|---|
| -32700 | Parse error | The request isn't valid JSON, or your `deserializer` raised. | The deserializer's exception message. |
| -32600 | Invalid request | The JSON isn't a valid request, a batch is empty, or a batch is bigger than `max_batch_size`. | "The request failed schema validation", or the batch size and the limit. |
| -32601 | Method not found | No method has that name. | The method name from the request. |
| -32602 | Invalid params | The params don't fit the method's signature. | Python's explanation, which names the parameter, such as "missing a required argument: 'name'". |
| -32603 | Internal error | The method raised an exception, returned something other than `Success` or `Error`, or returned a result the serializer couldn't handle. | None. With `debug=True`, the exception message. |
| -32000 | Server error | Something failed inside jsonrpcserver, outside any method. For example, a custom validator let through a request with no `method`. | None. With `debug=True`, the exception message. |

`debug` only changes the last two rows. The `data` in the other rows always
reaches the client. Keep that in mind if you write a custom deserializer,
because its exception messages are sent as they are.

!!! info "Changed in 5.0.10"
    From 5.0.0 to 5.0.9, the -32603 and -32000 errors always carried the
    exception message. It could hold passwords, paths or SQL. See
    [Security](security.md). 4.x had a `debug` option that hid it by default,
    and 5.0.10 brings that back.

## Four ways for a method to fail

```python
import logging

from jsonrpcserver import Error, InvalidParams, JsonRpcError, Result, Success, dispatch


def by_return(amount: int) -> Result:
    return Error(1, "Insufficient funds", {"balance": 10})


def by_raise(amount: int) -> Result:
    raise JsonRpcError(1, "Insufficient funds", {"balance": 10})


def bad_value(amount: int) -> Result:
    return InvalidParams("amount must be positive")


def by_accident(amount: int) -> Result:
    return Success(amount / 0)


methods = {
    "by_return": by_return,
    "by_raise": by_raise,
    "bad_value": bad_value,
    "by_accident": by_accident,
}
```

```pycon
>>> logging.disable(logging.CRITICAL)  # Keep the traceback out of this page.
>>> dispatch('{"jsonrpc": "2.0", "method": "by_return", "params": [50], "id": 1}', methods)
'{"jsonrpc": "2.0", "error": {"code": 1, "message": "Insufficient funds", "data": {"balance": 10}}, "id": 1}'
>>> dispatch('{"jsonrpc": "2.0", "method": "by_raise", "params": [50], "id": 1}', methods)
'{"jsonrpc": "2.0", "error": {"code": 1, "message": "Insufficient funds", "data": {"balance": 10}}, "id": 1}'
>>> dispatch('{"jsonrpc": "2.0", "method": "bad_value", "params": [-5], "id": 1}', methods)
'{"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params", "data": "amount must be positive"}, "id": 1}'
>>> dispatch(
...     '{"jsonrpc": "2.0", "method": "by_accident", "params": [50], "id": 1}', methods
... )
'{"jsonrpc": "2.0", "error": {"code": -32603, "message": "Internal error"}, "id": 1}'
>>> logging.disable(logging.NOTSET)
```

- **Return `Error`** for errors the client should know about. It's the
  normal way.
- **Raise `JsonRpcError`** when the error is found deep inside other
  functions. The response is the same as returning `Error`.
- **Return `InvalidParams`** when the arguments have the right shape but a
  bad value.
- **An uncaught exception** is a bug as far as the client is concerned. It
  gets a bare Internal error, and the details go to the log.

Errors you make on purpose are sent as they are, whatever `debug` is, so
don't put secrets in them.

## Debug mode

`debug=True` adds the exception message to the -32603 and -32000 errors, so
you can see what went wrong without reading the log:

```pycon
>>> logging.disable(logging.CRITICAL)
>>> dispatch(
...     '{"jsonrpc": "2.0", "method": "by_accident", "params": [50], "id": 1}',
...     methods,
...     debug=True,
... )
'{"jsonrpc": "2.0", "error": {"code": -32603, "message": "Internal error", "data": "division by zero"}, "id": 1}'
>>> logging.disable(logging.NOTSET)
```

Use it in development only. It's the same option on every dispatch function,
sync and async. It's new in 5.0.10.

## Spec warnings

The spec says an error code must be an integer, and the message should be a
string. It also reserves method names that start with `rpc.`. jsonrpcserver
warns about these with a `UserWarning`, but still sends what you gave it, so
existing code keeps working:

```pycon
>>> import warnings
>>> with warnings.catch_warnings(record=True) as caught:
...     warnings.simplefilter("always")
...     _ = Error("E1", "Insufficient funds")
>>> print(caught[0].message)
JSON-RPC error codes must be integers, not 'E1'
```

To make them errors in your tests, run pytest with `-W error::UserWarning`.
These warnings are new in 5.0.10. 6.0 may turn them into errors.

## Logging

Everything is logged on the `jsonrpcserver` logger or one of its children:

| Logger | What it logs |
|---|---|
| `jsonrpcserver.dispatcher` | For `dispatch`: an exception a method didn't catch (ERROR, with the traceback). A method that returned something other than `Success` or `Error` (ERROR). A failure inside jsonrpcserver (ERROR, with the traceback). |
| `jsonrpcserver.async_dispatcher` | The same, for `async_dispatch`. |
| `jsonrpcserver.main` | A result the serializer couldn't handle, such as a `datetime` (ERROR, with the traceback). Both sync and async. |
| `jsonrpcserver.server` | `serve()` only: where it's listening, and one line per HTTP request (INFO). |

Invalid requests, unknown methods and params that don't fit aren't logged.
The client gets the error, and it's not a problem with your server.

jsonrpcserver doesn't configure logging itself. If nothing configures it,
Python still prints warnings and errors to stderr, but without the time or the
logger's name. To see them properly, configure logging when your server
starts:

```python
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
)
```

To change only jsonrpcserver's messages, set the level or add a handler on
the parent logger: `logging.getLogger("jsonrpcserver")`.

This is what a method that returns a plain value, as it would in 4.x, looks
like in the log:

```python
import sys

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(name)s %(levelname)s: %(message)s"))
logging.getLogger("jsonrpcserver").addHandler(handler)


def ping() -> str:
    return "pong"  # Should be Success("pong")


dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}', {"ping": ping})
logging.getLogger("jsonrpcserver").removeHandler(handler)
```

```text title="Output"
jsonrpcserver.dispatcher ERROR: Method 'ping' returned 'pong', which is not a Result, so the client got an Internal error. Return Success(value) or Error(code, message). Since 5.0 a plain return value is not enough: https://bensynapse.github.io/jsonrpcserver/migration/
```

!!! info "New in 5.0.10"
    The `jsonrpcserver.main` messages and this one. Before 5.0.10, a
    serializer failure raised out of `dispatch`. A plain return value was
    logged with a traceback, and its explanation was also sent to the client
    in `data`.
