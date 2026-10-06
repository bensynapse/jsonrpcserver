"""A method is a Python function that can be called by a JSON-RPC request.

They're held in a dict, a mapping of function names to functions.

The @method decorator adds a method to jsonrpcserver's internal global_methods dict.
Alternatively pass your own dictionary of methods to `dispatch` with the methods param.

    >>> dispatch(request)  # Uses the internal collection of funcs added with @method
    >>> dispatch(request, methods={"ping": lambda: "pong"})  # Custom collection

Methods can take either positional or named arguments, but not both. This is a
limitation of JSON-RPC.
"""

import warnings
from typing import Any, Callable, Dict, Mapping, Optional, TypeVar, overload

from .result import Result

Method = Callable[..., Result]
Methods = Dict[str, Method]
# Async methods return a coroutine rather than a Result, so the dispatch functions
# accept any callable. They check what comes back at run time.
AnyMethod = Callable[..., Any]
# What the dispatch functions accept for their methods argument. Any mapping will do.
MethodsArgument = Mapping[str, AnyMethod]

global_methods: Dict[str, AnyMethod] = {}

F = TypeVar("F", bound=Callable[..., Any])


@overload
def method(f: F, name: Optional[str] = None) -> F: ...


@overload
def method(f: None = None, name: Optional[str] = None) -> Callable[[F], F]: ...


def method(f: Optional[F] = None, name: Optional[str] = None) -> Any:
    """A decorator to add a function into jsonrpcserver's internal global_methods dict.
    The global_methods dict will be used by default unless a methods argument is passed
    to `dispatch`.

    Functions can be renamed by passing a name argument:

        @method(name="bar")
        def foo():
            ...

    The decorated function is returned unchanged, so type checkers still see its real
    signature. A method with the same name as an earlier one replaces it.
    """

    def decorator(func: F) -> F:
        method_name = name or func.__name__
        if method_name.startswith("rpc."):
            warnings.warn(
                f"Method names starting with 'rpc.' are reserved by the JSON-RPC spec "
                f"({method_name!r})",
                stacklevel=3 if callable(f) else 2,
            )
        global_methods[method_name] = func
        return func

    return decorator(f) if callable(f) else decorator
