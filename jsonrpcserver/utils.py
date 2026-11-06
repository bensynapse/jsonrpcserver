"""Utility functions"""

from collections.abc import Callable
from functools import reduce
from typing import Any

# pylint: disable=invalid-name


def identity(x: Any) -> Any:
    """Returns the argument."""
    return x


def compose(*funcs: Callable[..., Any]) -> Callable[..., Any]:
    """Compose two or more functions producing a single composite function."""
    return reduce(lambda f, g: lambda *a, **kw: f(g(*a, **kw)), funcs)


def make_list(x: Any) -> list[Any]:
    """Puts a value into a list if it's not already."""
    # pyright can't tell the element type of a list narrowed from Any.
    return x if isinstance(x, list) else [x]  # pyright: ignore[reportUnknownVariableType]


def check_error(code: Any, message: Any) -> None:
    """Raise TypeError if an error's code or message breaks the JSON-RPC spec.

    The spec says code MUST be an integer and message SHOULD be a string. 5.0.10
    warned and sent them anyway, which some clients can't parse. Changed in 6.0:
    it raises.
    """
    if isinstance(code, bool) or not isinstance(code, int):
        raise TypeError(f"JSON-RPC error codes must be integers, not {code!r}")
    if not isinstance(message, str):
        raise TypeError(f"JSON-RPC error messages must be strings, not {message!r}")
