---
description: Write JSON-RPC methods with jsonrpcserver. The @method decorator, renaming, returning Success or Error, raising JsonRpcError, and how parameters are checked.
---

# Methods

Methods are the functions a JSON-RPC request can call. To write one, decorate
a function with `@method`, and return `Success` with the result:

```python
from jsonrpcserver import Error, InvalidParams, Result, Success, dispatch, method


@method
def ping() -> Result:
    return Success("pong")
```

The decorator adds the function to a dict of methods inside jsonrpcserver,
which `dispatch` uses by default. It returns the function unchanged, so you
can still call it yourself.

To use a different name in requests, pass `name`:

```python
@method(name="sum")
def add_numbers(a: int, b: int) -> Result:
    return Success(a + b)
```

```pycon
>>> dispatch('{"jsonrpc": "2.0", "method": "sum", "params": [2, 3], "id": 1}')
'{"jsonrpc": "2.0", "result": 5, "id": 1}'
```

A later `@method` with the same name replaces the earlier one, without a
warning. If you'd rather not use a decorator, pass the methods to `dispatch`
yourself as a dict. See [methods](dispatch.md#methods) on the Dispatch page.

!!! info "New in 5.0.10"
    A name that starts with `rpc.` gives a `UserWarning`, because the
    JSON-RPC spec reserves those names. The method is still added.

## Results

A method returns `Success` or `Error`. They are the `result` and `error` parts
of a [JSON-RPC response](https://www.jsonrpc.org/specification#response_object).
jsonrpcserver adds the `jsonrpc` and `id` parts.

!!! warning "Return `Success(value)`, not the value"
    In 4.x a method returned its result directly. In 5.x, `return "pong"`
    sends the client a -32603 "Internal error", with no details. The log
    says what went wrong. See [Migration](migration.md).

`Success` takes the result value. If there's nothing to return, call it with
no argument and the result is `null`:

```python
@method
def log(message: str) -> Result:
    return Success()
```

```pycon
>>> dispatch('{"jsonrpc": "2.0", "method": "log", "params": ["hi"], "id": 1}')
'{"jsonrpc": "2.0", "result": null, "id": 1}'
```

`Error` takes a code, a message and, optionally, some data:

```python
@method
def divide(a: float, b: float) -> Result:
    if b == 0:
        return Error(1, "Can't divide by zero", {"a": a})
    return Success(a / b)
```

```pycon
>>> dispatch('{"jsonrpc": "2.0", "method": "divide", "params": [1, 0], "id": 1}')
'{"jsonrpc": "2.0", "error": {"code": 1, "message": "Can\'t divide by zero", "data": {"a": 1}}, "id": 1}'
```

The spec says the code must be an integer and the message should be a string.
The spec reserves the codes from -32768 to -32000 for its own errors, so pick
other numbers for yours.

!!! info "New in 5.0.10"
    `Error` and `JsonRpcError` give a `UserWarning` if the code isn't an
    integer or the message isn't a string. The error is still sent as given,
    so existing code keeps working, but some clients can't read it.

You can also raise `JsonRpcError`, which takes the same arguments as `Error`.
That's handy deep inside other functions:

```python
from jsonrpcserver import JsonRpcError


def check_positive(number: float) -> None:
    if number < 0:
        raise JsonRpcError(2, "Must be positive")


@method
def square_root(number: float) -> Result:
    check_positive(number)
    return Success(number**0.5)
```

```pycon
>>> dispatch('{"jsonrpc": "2.0", "method": "square_root", "params": [-4], "id": 1}')
'{"jsonrpc": "2.0", "error": {"code": 2, "message": "Must be positive"}, "id": 1}'
```

Any other exception gives a -32603 "Internal error" response. The exception
isn't sent to the client, but it is logged. See
[Errors and logging](errors.md).

## Parameters

Positional and named parameters both work. jsonrpcserver checks the request's
`params` against the function's signature before calling it:

```python
@method
def hello(name: str) -> Result:
    return Success("Hello " + name)
```

```pycon
>>> dispatch('{"jsonrpc": "2.0", "method": "hello", "params": ["Beau"], "id": 1}')
'{"jsonrpc": "2.0", "result": "Hello Beau", "id": 1}'
>>> dispatch('{"jsonrpc": "2.0", "method": "hello", "params": {"name": "Beau"}, "id": 1}')
'{"jsonrpc": "2.0", "result": "Hello Beau", "id": 1}'
```

If they don't fit, the client gets -32602 "Invalid params", with Python's
explanation in `data`:

```pycon
>>> dispatch('{"jsonrpc": "2.0", "method": "hello", "params": [], "id": 1}')
'{"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params", "data": "missing a required argument: \'name\'"}, "id": 1}'
```

A request's `params` is either a list or an object, so a method can't get some
arguments by position and others by name. That's a JSON-RPC rule.

jsonrpcserver doesn't check the types of the values. A method gets whatever
JSON gave: `str`, `int`, `float`, `bool`, `None`, `list` or `dict`. The client
also chooses which of your parameters to fill, including ones with default
values. [Security](security.md#every-parameter-is-up-to-the-client) explains
why that matters.

## Invalid params

To reject values yourself, return `InvalidParams`. It's a shortcut for
`Error(-32602, "Invalid params", data)`:

```python
@method
def rate(stars: int) -> Result:
    if stars not in range(1, 6):
        return InvalidParams("Stars must be 1 to 5")
    return Success()
```

```pycon
>>> dispatch('{"jsonrpc": "2.0", "method": "rate", "params": [6], "id": 1}')
'{"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params", "data": "Stars must be 1 to 5"}, "id": 1}'
```

## Async methods

Methods can be `async def` functions too. Call them with `async_dispatch`
instead of `dispatch`. See [Async](async.md).

## Type checking

`@method` keeps the function's signature, so mypy and pyright check your
methods and the calls to them. [Typing](typing.md) has the details, including
one setting mypy needs.
