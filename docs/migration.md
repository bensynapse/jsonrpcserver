---
description: Upgrade jsonrpcserver from 5.x to 6.0, from 4.x to 5.x, and from 5.0.9 to 5.0.10. What changed in 6.0, with the replacement for each removed name, and side-by-side examples for 4.x code.
---

# Migration

## From 5.x to 6.0

Code that registers methods with `@method`, returns `Success(...)`,
`Error(...)` or a plain value, and calls `dispatch` or `async_dispatch` keeps
working. A test in the repository pins that. The rest of this section lists
everything that changed, so you can check your own code against it.

### Python 3.11 or later

6.0 needs Python 3.11 or later. 3.8, 3.9 and 3.10 have reached end of life.
On an older Python, `pip install jsonrpcserver` keeps installing 5.x.

### Results and responses are dataclasses

5.x built results and responses on the oslash library's `Right` and `Left`.
6.0 has no dependencies, and they're plain frozen dataclasses:

| 5.x | 6.0 |
|---|---|
| `Success(x)` is a `Right` holding a `SuccessResult` | `Success(x)` is a `SuccessResult` |
| `Error(...)` is a `Left` holding an `ErrorResult` | `Error(...)` is an `ErrorResult` |
| `isinstance(response, Left)` | `isinstance(response, ErrorResponse)` |
| `response._value.result` | `response.result` |
| `response._error.code` | `response.code` |
| `from oslash.either import Left, Right` | not needed |
| a mypy setting for oslash | not needed |

Code that reads responses from `dispatch_to_response`, or that a
`post_process` function receives, needs the change in the table. Code that
only uses `dispatch`, `async_dispatch` or `dispatch_to_serializable` doesn't.

`InvalidResultError`, `validate_result` and `log_invalid_result` are gone
from `jsonrpcserver.dispatcher`. Without the wrappers there's no invalid
Result left: whatever a method returns is its result.

### Requests are checked without jsonschema

The default validator checks the same rules as before, without the
jsonschema library. It raises
`jsonrpcserver.validator.InvalidRequestError`, and the client gets the same
-32600 response. `jsonrpcserver/request-schema.json` is gone. If you
imported it, copy it from 5.x. Dispatching is about four times faster for a
small method.

### Safer defaults

| | 5.x | 6.0 | To get the 5.x behaviour |
|---|---|---|---|
| Batch size | no limit | 100 requests | `max_batch_size=None` |
| `NaN`, `Infinity`, `1e400` in a request | accepted | -32700 Parse error | `deserializer=json.loads` |
| `Error` or `JsonRpcError` with a non-integer code or a non-string message | `UserWarning`, sent as given | `TypeError` | none: fix the code or message |
| `@method` name starting with `rpc.` | `UserWarning`, added | `ValueError` | none: rename the method |
| `serve()` with no host | every network interface | localhost only | `serve("", port)` |

`dispatch_to_response` used `json.loads` as its default deserializer, unlike
the other dispatch functions. It uses the same default as them now.

### Removed names

| Removed | Use |
|---|---|
| `jsonrpcserver.response.serialize_error` | `to_error_dict` |
| `jsonrpcserver.response.serialize_success` | `to_success_dict` |
| `jsonrpcserver.response.to_serializable_one`, `jsonrpcserver.main.to_serializable_one` | `to_dict` |
| `jsonrpcserver.response.ResponseType` | `Response` |

All four gave a `DeprecationWarning` from 5.0.10.

### New

`max_concurrency` on the async dispatch functions limits how many requests of
a batch run at once. See [Async](async.md#limit-how-many-run-at-once).

## From 4.x to 5.x

Version 5 changed how methods report their result. Most other code needs only
small changes.

!!! danger "Old methods fail with no details before 5.1.0"
    In 4.x a method returned its result directly. In 5.0.x it must return
    `Success(result)`. From 5.1.0 a plain return value works again, and
    becomes `Success(value)`. On 5.0.x, a 4.x method such as

    <!-- skip: 4.x code -->
    ```python
    @method
    def ping():
        return "pong"
    ```

    still runs, but the client gets a -32603 "Internal error". Up to 5.0.9,
    its `data` says "The method did not return a valid Result". From 5.0.10
    the client gets no details, and the log says what's wrong:

    ```text
    Method 'ping' returned 'pong', which is not a Result, so the client got an Internal error. Return Success(value) or Error(code, message). ...
    ```

    That's the 5.0.10 message. Upgrading to 5.1.0 fixes these methods
    without a code change.

    If you don't see that line, configure logging (see
    [Errors and logging](errors.md#logging)). Then search your code for
    `return` statements in methods. mypy and pyright catch them too, once
    methods are annotated `-> Result` (see [Typing](typing.md)).

### A method, before and after

4.x:

<!-- skip: 4.x code -->
```python
# jsonrpcserver 4.x. This doesn't work on 5.x.
from jsonrpcserver import dispatch, method
from jsonrpcserver.exceptions import ApiError, InvalidParamsError


@method
def divide(a, b):
    if not isinstance(b, (int, float)):
        raise InvalidParamsError("b must be a number")
    if b == 0:
        raise ApiError("Can't divide by zero", code=1)
    return a / b


response = dispatch(request_body)
if response.wanted:
    send(str(response), status=response.http_status)
```

5.x:

```python
from jsonrpcserver import Error, InvalidParams, Result, Success, dispatch, method


@method
def divide(a: float, b: float) -> Result:
    if not isinstance(b, (int, float)):
        return InvalidParams("b must be a number")
    if b == 0:
        return Error(1, "Can't divide by zero")
    return Success(a / b)


response = dispatch('{"jsonrpc": "2.0", "method": "divide", "params": [1, 0], "id": 1}')
print(response, 200 if response else 204)
```

```text title="Output"
{"jsonrpc": "2.0", "error": {"code": 1, "message": "Can't divide by zero"}, "id": 1} 200
```

### What changed

| 4.x | 5.x |
|---|---|
| `return value` | `return Success(value)`. From 5.1.0 `return value` works too |
| `raise ApiError(message, code=1, data=...)` | `return Error(code, message, data)`, or `raise JsonRpcError(code, message, data)`. Note the order: code first. |
| `raise InvalidParamsError(...)` | `return InvalidParams(data)` |
| `raise MethodNotFoundError` | there's no equivalent. jsonrpcserver sends "Method not found" itself |
| `dispatch` returns a `Response` object | `dispatch` returns a string. `dispatch_to_serializable` gives a dict |
| `str(response)` | `response` is already the string |
| `response.wanted` | `if response:`, since a notification gives `""` |
| `response.http_status` | `200 if response else 204`. Errors are sent with 200 too |
| `methods = Methods(ping, add)`, `methods.add(...)` | a plain dict, `{"ping": ping, "add": add}`, or `@method` |
| `dispatch(..., serialize=..., deserialize=...)` | `serializer=` and `deserializer=` |
| `convert_camel_case=True` | removed. Name your methods and parameters as clients call them |
| `basic_logging=True`, `trim_log_values=True` | removed. Configure the `jsonrpcserver` logger yourself |
| a `.jsonrpcserverrc` config file | removed. Pass options to `dispatch` |
| `debug=True` | removed in 5.0.0, so 5.0.0 to 5.0.9 always send exception messages to the client. Back in 5.0.10, where it works as in 4.x: off by default |

Code written for 4.x that 5.x can't run gives clear errors in most cases. The
removed keywords raise `TypeError`, and `response.wanted` raises
`AttributeError: 'str' object has no attribute 'wanted'`. The plain return
value above is the one that fails quietly before 5.1.0, and `str(response)` still works but
is no longer needed.

The 4.x documentation is no longer online. The [changelog](changelog.md)
lists every 4.x change.

## From 5.0.9 to 5.0.10

Most code needs no change. These are the differences you might notice.

**Exception messages are no longer sent.** A method that raises an exception
it doesn't catch gives a -32603 "Internal error" with no `data`. Clients that
read `error.data` for those errors get nothing now. The exception is logged.
Pass `debug=True` in development to get the message back in the response. See
[Security](security.md).

**Custom validators see one request at a time.** In a batch, the `validator`
is called once for each request, with just that request. In 5.0.9 it was
called once with the whole list. A validator that enforced a rule about the
whole batch, such as a size limit, silently stops doing it. Use
`max_batch_size` instead. See [Validation](validation.md).

**Batches are handled per request.** A batch that mixes valid and invalid
requests used to get one "Invalid request" for the whole batch. Now each
invalid request gets its own error, and the valid ones run. See
[Notifications and batches](batches.md#invalid-members).

**NaN and Infinity give an error.** A result that contains `NaN`, `Infinity`
or `-Infinity` now gives an Internal error, because they aren't valid JSON. To
send them anyway, pass `serializer=json.dumps`.

**A result that can't be serialized gives an error.** For example a
`datetime`. In 5.0.9 `dispatch` raised `TypeError`. Now that response becomes
an Internal error, the error is logged, and the rest of a batch is sent.

**New warnings.** `Error` and `JsonRpcError` warn when the code isn't an
integer or the message isn't a string, and `@method` warns about names that
start with `rpc.`. The responses are the same as before. If your tests turn
warnings into errors, fix the code or the names. See
[Errors and logging](errors.md#spec-errors).

**Deprecated names.** In `jsonrpcserver.response`, `serialize_error`,
`serialize_success` and `to_serializable_one` give a `DeprecationWarning`. Use
`to_error_dict`, `to_success_dict` and `to_dict`. `ResponseType` is kept, but
use `Response`. They will be removed in 6.0.

**New loggers and log lines.** A serializer failure is logged on
`jsonrpcserver.main`, and `serve()` logs where it's listening. A method that
returns a plain value is logged with a hint instead of a traceback. See
[Errors and logging](errors.md#logging).

**Plain methods work with `async_dispatch`.** In 5.0.9 they gave an Internal
error.

**`serve()` sends 204 for a notification**, instead of 200 with an empty
body, and answers bad requests instead of dropping the connection.

**New features you can use:** `max_batch_size` and `debug` on every dispatch
function, `jsonrpcserver.__version__`, and type checking that sees through
`@method` (see [Typing](typing.md)).

**Python 3.8 or later.** 5.0.10's package metadata says so, so older Pythons
keep installing 5.0.9.
