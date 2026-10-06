---
description: Type checking jsonrpcserver code with mypy and pyright. What Result is, why mypy needs one setting for oslash, and how @method keeps your function's signature.
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

`Result` is the return type of a method. `Success`, `Error` and
`InvalidParams` all return one. It comes from the
[oslash](https://pypi.org/project/oslash/) library: it's an `Either`, a
`Right` holding a `SuccessResult` or a `Left` holding an `ErrorResult`. You
don't need to look inside it. Return it, and annotate your methods with it.

```pycon
>>> from jsonrpcserver import Error, Success
>>> from oslash.either import Left, Right
>>> isinstance(Success("pong"), Right)
True
>>> isinstance(Error(1, "Failed"), Left)
True
```

The [Dispatch](dispatch.md#dispatch_to_response) page shows how to read the
`Response` objects that `dispatch_to_response` gives, which work the same
way. The [roadmap](roadmap.md) plans to replace oslash in 6.0.

## mypy needs one setting

oslash has type hints but no `py.typed` marker. pyright reads them anyway.
mypy treats `Result` as `Any` unless you add this to `pyproject.toml`:

```toml
[[tool.mypy.overrides]]
module = ["oslash", "oslash.*"]
follow_untyped_imports = true
```

Without it, mypy can't tell a method that returns `Success(...)` from one that
returns a plain value, which would give an Internal error at run time.

## Async methods

`async def` methods that return `Result` type-check too, and both `dispatch`
and `async_dispatch` accept them in `methods`. Only `async_dispatch` can
call them. See [Async](async.md).
