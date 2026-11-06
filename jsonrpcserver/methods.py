"""Methods: the functions a JSON-RPC request can call.

The dispatch functions look methods up in a dict of names to functions. The @method
decorator adds a function to global_methods, the dict they use by default. To use
your own dict instead, pass it as the methods argument:

    dispatch(request)  # the functions registered with @method
    dispatch(request, methods={"ping": ping})  # only the functions in this dict

Either way, a method returns Success(...) or Error(...). From 5.1.0 it can also
return a plain value, which becomes Success(value).

A request's params are either a list (positional arguments) or an object (named
arguments), not both. That's a JSON-RPC rule.
"""

from collections.abc import Callable, Mapping
from typing import Any, TypeVar, overload

from .result import Result

Method = Callable[..., Result]
Methods = dict[str, Method]
# Async methods return a coroutine rather than a Result, so the dispatch functions
# accept any callable. They check what comes back at run time.
AnyMethod = Callable[..., Any]
# What the dispatch functions accept for their methods argument. Any mapping will do.
MethodsArgument = Mapping[str, AnyMethod]

global_methods: dict[str, AnyMethod] = {}
"""The methods registered with `@method`, as a dict of names to functions.

The dispatch functions use it when they're called without `methods`. It's shared by
the whole process, so every module that uses `@method` adds to it.
"""

F = TypeVar("F", bound=Callable[..., Any])


@overload
def method(f: F, name: str | None = None) -> F: ...


@overload
def method(f: None = None, name: str | None = None) -> Callable[[F], F]: ...


def method(f: Callable[..., Any] | None = None, name: str | None = None) -> Any:
    """Register a function as a JSON-RPC method.

    The function is added to `global_methods`, which the dispatch functions use when
    they're called without `methods`. It's returned unchanged, so you can still call
    it yourself, and type checkers see its real signature (from 5.0.10). A method
    with the same name as an earlier one replaces it, without a warning.

    Use it with or without arguments:

    ```python
    @method
    def ping() -> Result:
        return Success("pong")

    @method(name="sum")
    def add(a: int, b: int) -> Result:
        return Success(a + b)
    ```

    Args:
        f: The function. Leave it out to pass `name`.
        name: The name requests use to call the method. The default is the
            function's name.

    Returns:
        The function itself, or, when called with only `name`, a decorator.

    Raises:
        ValueError: If the name starts with "rpc.". The JSON-RPC spec reserves those
            names. Changed in 6.0: 5.0.10 warned and added the method anyway.
    """

    def decorator(func: F) -> F:
        method_name = func.__name__ if name is None else name
        if method_name.startswith("rpc."):
            raise ValueError(
                f"Method names starting with 'rpc.' are reserved by the JSON-RPC spec "
                f"({method_name!r})"
            )
        global_methods[method_name] = func
        return func

    return decorator(f) if callable(f) else decorator
