"""Test response.py"""

import importlib
from unittest.mock import sentinel

import pytest

from jsonrpcserver.response import (
    ErrorResponse,
    InvalidRequestResponse,
    MethodNotFoundResponse,
    ParseErrorResponse,
    ServerErrorResponse,
    SuccessResponse,
    to_serializable,
)

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
    assert to_serializable(SuccessResponse(sentinel.result, sentinel.id)) == {
        "jsonrpc": "2.0",
        "result": sentinel.result,
        "id": sentinel.id,
    }


def test_to_serializable_None() -> None:
    assert to_serializable(None) is None


def test_to_serializable_SuccessResponse() -> None:
    assert to_serializable(SuccessResponse(sentinel.result, sentinel.id)) == {
        "jsonrpc": "2.0",
        "result": sentinel.result,
        "id": sentinel.id,
    }


def test_to_serializable_ErrorResponse() -> None:
    assert to_serializable(
        ErrorResponse(sentinel.code, sentinel.message, sentinel.data, sentinel.id)
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
    assert to_serializable([SuccessResponse(sentinel.result, sentinel.id)]) == [
        {
            "jsonrpc": "2.0",
            "result": sentinel.result,
            "id": sentinel.id,
        }
    ]


@pytest.mark.parametrize(
    "module,name",
    [
        ("response", "serialize_error"),
        ("response", "serialize_success"),
        ("response", "to_serializable_one"),
        ("response", "ResponseType"),
        ("main", "to_serializable_one"),
    ],
)
def test_names_deprecated_in_5_are_gone(module: str, name: str) -> None:
    """Deprecated in 5.0.10 and removed in 6.0 (plans/6.0.md, D10)."""
    imported = importlib.import_module(f"jsonrpcserver.{module}")
    assert not hasattr(imported, name)
