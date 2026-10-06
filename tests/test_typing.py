"""Type checking regressions.

mypy (warn_unused_ignores, part of --strict) and pyright
(reportUnnecessaryTypeIgnoreComment) both fail if a "type: ignore" comment below stops
being needed. So if @method went back to erasing the decorated function's signature, the
type check in CI would fail.
"""

from typing import TYPE_CHECKING

from jsonrpcserver import Error, Result, Success, method
from jsonrpcserver.methods import global_methods


@method(name="typing_add")
def add(a: int, b: int) -> Result:
    return Success(a + b)


@method
def typing_sub(a: int, b: int) -> Result:
    return Success(a - b)


@method
async def typing_async(a: int) -> Result:
    return Success(a)


def test_decorated_functions_are_unchanged() -> None:
    assert global_methods["typing_add"] is add
    assert global_methods["typing_sub"] is typing_sub
    assert global_methods["typing_async"] is typing_async
    assert add(1, 2) == Success(3)


if TYPE_CHECKING:
    # @method keeps the signature, so a wrong argument type is an error.
    add("1", 2)  # type: ignore[arg-type]
    typing_sub(1)  # type: ignore[call-arg]

    # Result is a real type, not Any.
    not_an_int: int = Success(1)  # type: ignore[assignment]

    # Error's code must be an int.
    Error("abc", "message")  # type: ignore[arg-type]
