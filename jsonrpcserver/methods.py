"""A method is a Python function that can be called by a JSON-RPC request.

They're held in a dict, a mapping of function names to functions.

The @method decorator adds a method to jsonrpcserver's internal global_methods dict.
Alternatively pass your own dictionary of methods to `dispatch` with the methods param.

    >>> dispatch(request)  # Uses the internal collection of funcs added with @method
    >>> dispatch(request, methods={"ping": lambda: "pong"})  # Custom collection

Methods can take either positional or named arguments, but not both. This is a
limitation of JSON-RPC.
"""

from typing import Any, Callable, Dict, Optional, cast

from .result import Result

Method = Callable[..., Result]
Methods = Dict[str, Method]

global_methods: Methods = {}


def method(
    f: Optional[Method] = None,  # pylint: disable=invalid-name
    name: Optional[str] = None,
) -> Callable[..., Any]:
    """A decorator to add a function into jsonrpcserver's internal global_methods dict.
    The global_methods dict will be used by default unless a methods argument is passed
    to `dispatch`.

    Functions can be renamed by passing a name argument:

        @method(name=bar)
        def foo():
            ...
    """

    def decorator(func: Method) -> Method:
        nonlocal name
        global_methods[name or func.__name__] = func
        return func

    return decorator(f) if callable(f) else cast(Method, decorator)
