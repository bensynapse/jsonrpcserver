"""Utility functions"""

import warnings
from functools import reduce
from typing import Any, Callable, List, TypeVar, cast

from oslash.either import Either, Right

T = TypeVar("T")

# pylint: disable=invalid-name


def identity(x: Any) -> Any:
    """Returns the argument."""
    return x


def compose(*funcs: Callable[..., Any]) -> Callable[..., Any]:
    """Compose two or more functions producing a single composite function."""
    return reduce(lambda f, g: lambda *a, **kw: f(g(*a, **kw)), funcs)


def make_list(x: Any) -> List[Any]:
    """Puts a value into a list if it's not already."""
    # pyright can't tell the element type of a list narrowed from Any.
    return x if isinstance(x, list) else [x]  # pyright: ignore[reportUnknownVariableType]


def warn_if_invalid_error(code: Any, message: Any, stacklevel: int) -> None:
    """Warn if an error's code or message breaks the JSON-RPC spec.

    The spec says code MUST be an integer and message SHOULD be a string. These used to
    be sent as given, which some clients can't parse. It's a warning, not an error,
    so existing code keeps working.
    """
    if isinstance(code, bool) or not isinstance(code, int):
        warnings.warn(
            f"JSON-RPC error codes must be integers, not {code!r}",
            stacklevel=stacklevel + 1,
        )
    if not isinstance(message, str):
        warnings.warn(
            f"JSON-RPC error messages should be strings, not {message!r}",
            stacklevel=stacklevel + 1,
        )


def unwrap(either: Either[T, Any]) -> T:
    """The value inside a Right. Only call this once you know it isn't a Left."""
    return cast("Right[T, Any]", either)._value
