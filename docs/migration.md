---
description: Upgrade jsonrpcserver from 4.x to 5.x, and from 5.0.9 to 5.0.10. Side-by-side examples, removed options, and the plain return value that silently becomes an Internal error.
---

# Migration

## From 4.x to 5.x

Version 5 changed how methods report their result. Most other code needs only
small changes.

!!! danger "Old methods fail with no details"
    In 4.x a method returned its result directly. In 5.x it must return
    `Success(result)`. A 4.x method such as

    <!-- skip: 4.x code -->
    ```python
    @method
    def ping():
        return "pong"
    ```

    still runs, but the client gets `{"code": -32603, "message": "Internal
    error"}` with no details. From 5.0.10 the log says what's wrong:

    ```text
    Method 'ping' returned 'pong', which is not a Result, so the client got an Internal error. Return Success(value) or Error(code, message). ...
    ```

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
| `return value` | `return Success(value)` |
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
| `debug=True` | still there. In 5.0.10 it controls whether exception messages reach the client |

Code written for 4.x that 5.x can't run gives clear errors in most cases. The
removed keywords raise `TypeError`, and `response.wanted` raises
`AttributeError: 'str' object has no attribute 'wanted'`. The plain return
value above is the one that fails quietly, and `str(response)` still works but
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
is called once for each request, with that request's dict. In 5.0.9 it was
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
[Errors and logging](errors.md#spec-warnings).

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
