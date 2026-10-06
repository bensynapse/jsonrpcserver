"""Test response.py"""

import subprocess
import sys
from typing import Any
from unittest.mock import sentinel

import pytest
from oslash.either import Left, Right

from jsonrpcserver.response import (
    ErrorResponse,
    InvalidRequestResponse,
    MethodNotFoundResponse,
    ParseErrorResponse,
    ServerErrorResponse,
    SuccessResponse,
    to_serializable,
)
from jsonrpcserver.sentinels import NODATA

# pylint: disable=missing-function-docstring,invalid-name,duplicate-code


def test_SuccessResponse() -> None:
    response = SuccessResponse(sentinel.result, sentinel.id)
    assert response.result == sentinel.result
    assert response.id == sentinel.id


def test_ErrorResponse() -> None:
    response = ErrorResponse(
        sentinel.code, sentinel.message, sentinel.data, sentinel.id
    )
    assert response.code is sentinel.code
    assert response.message is sentinel.message
    assert response.data is sentinel.data
    assert response.id is sentinel.id


def test_ParseErrorResponse() -> None:
    response = ParseErrorResponse(sentinel.data)
    assert response.code == -32700
    assert response.message == "Parse error"
    assert response.data == sentinel.data
    assert response.id is None


def test_InvalidRequestResponse() -> None:
    response = InvalidRequestResponse(sentinel.data)
    assert response.code == -32600
    assert response.message == "Invalid request"
    assert response.data == sentinel.data
    assert response.id is None


def test_MethodNotFoundResponse() -> None:
    response = MethodNotFoundResponse(sentinel.data, sentinel.id)
    assert response.code == -32601
    assert response.message == "Method not found"
    assert response.data == sentinel.data
    assert response.id == sentinel.id


def test_ServerErrorResponse() -> None:
    response = ServerErrorResponse(sentinel.data, sentinel.id)
    assert response.code == -32000
    assert response.message == "Server error"
    assert response.data == sentinel.data
    assert response.id == sentinel.id


def test_to_serializable() -> None:
    assert to_serializable(Right(SuccessResponse(sentinel.result, sentinel.id))) == {
        "jsonrpc": "2.0",
        "result": sentinel.result,
        "id": sentinel.id,
    }


def test_to_serializable_None() -> None:
    assert to_serializable(None) is None


def test_to_serializable_SuccessResponse() -> None:
    assert to_serializable(Right(SuccessResponse(sentinel.result, sentinel.id))) == {
        "jsonrpc": "2.0",
        "result": sentinel.result,
        "id": sentinel.id,
    }


def test_to_serializable_ErrorResponse() -> None:
    assert to_serializable(
        Left(ErrorResponse(sentinel.code, sentinel.message, sentinel.data, sentinel.id))
    ) == {
        "jsonrpc": "2.0",
        "error": {
            "code": sentinel.code,
            "message": sentinel.message,
            "data": sentinel.data,
        },
        "id": sentinel.id,
    }


def test_to_serializable_list() -> None:
    assert to_serializable([Right(SuccessResponse(sentinel.result, sentinel.id))]) == [
        {
            "jsonrpc": "2.0",
            "result": sentinel.result,
            "id": sentinel.id,
        }
    ]


# The 5.0.9 names


@pytest.mark.parametrize(
    "old,new,argument",
    [
        ("serialize_error", "to_error_dict", ErrorResponse(1, "foo", NODATA, 1)),
        ("serialize_success", "to_success_dict", SuccessResponse("foo", 1)),
        (
            "to_serializable_one",
            "to_dict",
            Right[SuccessResponse, ErrorResponse](SuccessResponse("foo", 1)),
        ),
    ],
)
def test_deprecated_names(old: str, new: str, argument: Any) -> None:
    from jsonrpcserver import response

    with pytest.warns(DeprecationWarning, match=f"Use {new} instead") as record:
        result = getattr(response, old)(argument)
    assert result == getattr(response, new)(argument)
    # The warning points at the caller, not at jsonrpcserver.
    assert record[0].filename == __file__


def test_to_serializable_one_importable_from_main() -> None:
    from jsonrpcserver.main import to_serializable_one

    with pytest.warns(DeprecationWarning):
        assert to_serializable_one(Left(ErrorResponse(1, "foo", NODATA, 1))) == {
            "jsonrpc": "2.0",
            "error": {"code": 1, "message": "foo"},
            "id": 1,
        }


def test_import_has_no_deprecation_warning() -> None:
    """importlib.resources.read_text warned on Python 3.11 and 3.12."""
    code = "import jsonrpcserver"
    subprocess.run(
        [sys.executable, "-W", "error::DeprecationWarning", "-c", code], check=True
    )
