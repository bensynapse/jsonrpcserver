"""Result data types - the results of calling a method.

Results are the JSON-RPC response objects
(https://www.jsonrpc.org/specification#response_object), minus the "jsonrpc" and "id"
parts - the library takes care of these parts for you.

The public functions are Success, Error and InvalidParams.
"""

from typing import Any, NamedTuple

from oslash.either import Either, Left, Right  # type: ignore

from .codes import ERROR_INTERNAL_ERROR, ERROR_INVALID_PARAMS, ERROR_METHOD_NOT_FOUND
from .sentinels import NODATA

# pylint: disable=missing-class-docstring,missing-function-docstring,invalid-name


class SuccessResult(NamedTuple):
    result: Any = None

    def __repr__(self) -> str:
        return f"SuccessResult({self.result!r})"


class ErrorResult(NamedTuple):
    code: int
    message: str
    data: Any = NODATA  # The spec says this value may be omitted

    def __repr__(self) -> str:
        return (
            f"ErrorResult(code={self.code!r}, message={self.message!r}, "
            f"data={self.data!r})"
        )


# Union of the two valid result types
Result = Either[ErrorResult, SuccessResult]


# Helpers


def MethodNotFoundResult(data: Any) -> ErrorResult:
    return ErrorResult(ERROR_METHOD_NOT_FOUND, "Method not found", data)


def InternalErrorResult(data: Any) -> ErrorResult:
    return ErrorResult(ERROR_INTERNAL_ERROR, "Internal error", data)


def InvalidParamsResult(data: Any = NODATA) -> ErrorResult:
    return ErrorResult(ERROR_INVALID_PARAMS, "Invalid params", data)


# Helpers (the public functions)


def Success(*args: Any, **kwargs: Any) -> Either[ErrorResult, SuccessResult]:
    return Right(SuccessResult(*args, **kwargs))


def Error(*args: Any, **kwargs: Any) -> Either[ErrorResult, SuccessResult]:
    return Left(ErrorResult(*args, **kwargs))


def InvalidParams(*args: Any, **kwargs: Any) -> Either[ErrorResult, SuccessResult]:
    """InvalidParams is a shortcut to save you from having to pass the Invalid Params
    JSON-RPC code to Error.
    """
    return Left(InvalidParamsResult(*args, **kwargs))
