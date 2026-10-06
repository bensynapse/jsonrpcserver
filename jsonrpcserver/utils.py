"""Utility functions"""

from functools import reduce
from typing import Any, Callable, List

# pylint: disable=invalid-name


def identity(x: Any) -> Any:
    """Returns the argument."""
    return x


def compose(*funcs: Callable[..., Any]) -> Callable[..., Any]:
    """Compose two or more functions producing a single composite function."""
    return reduce(lambda f, g: lambda *a, **kw: f(g(*a, **kw)), funcs)


def make_list(x: Any) -> List[Any]:
    """Puts a value into a list if it's not already."""
    return x if isinstance(x, list) else [x]
