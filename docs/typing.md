---
description: Type checking jsonrpcserver code with mypy and pyright. What Result is, and how @method keeps your function's signature.
---

# Typing

jsonrpcserver ships type hints (it has a `py.typed` marker), and its own code
is checked with mypy and pyright in strict mode.

## Methods keep their signature

`@method` returns your function unchanged, so type checkers see its real
signature. Calls to your methods from your own code are checked as usual:

```python
from jsonrpcserver import Result, Success, method


@method
def add(a: int, b: int) -> Result:
    return Success(a + b)


add(1, 2)  # fine
# add("1", 2) is a type error: "str" is not "int".
```

!!! info "New in 5.0.10"
    Before 5.0.10, type checkers saw every function decorated with `@method`
    as `(*Any, **Any) -> Any`. They couldn't check calls to it.

The values in a request aren't checked against these hints at run time.
jsonrpcserver only checks that the arguments fit the signature, so `add`
can still receive a string from a client. Check values in the method if it
matters.

## What Result is

`Result` is the return type of a method: `SuccessResult | ErrorResult`.
`Success` returns a `SuccessResult`, and `Error` and `InvalidParams` return an
`ErrorResult`. Both are frozen dataclasses.

```pycon
>>> from jsonrpcserver import Error, Success
>>> from jsonrpcserver.result import ErrorResult
>>> Success("pong")
SuccessResult('pong')
>>> isinstance(Error(1, "Failed"), ErrorResult)
True
```

A method can also return a plain value, which is sent as the result. Annotate
it with the value's type, or with `Result` if it can return an error too.

The [Dispatch](dispatch.md#dispatch_to_response) page shows the `Response`
objects that `dispatch_to_response` gives, which work the same way.

!!! info "Changed in 6.0"
    5.x built `Result` on the oslash library, and mypy needed a setting to
    read its types. jsonrpcserver has no dependencies now, so mypy and pyright
    need no settings.

## Async methods

`async def` methods that return `Result` type-check too, and both `dispatch`
and `async_dispatch` accept them in `methods`. Only `async_dispatch` can
call them. See [Async](async.md).
