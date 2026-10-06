"""Test dispatcher.py

TODO: Add tests for dispatch_requests (non-pure version)
"""

import json
from typing import Any, Callable, Dict
from unittest.mock import Mock, patch, sentinel

import pytest
from oslash.either import Left, Right  # type: ignore

from jsonrpcserver.codes import (
    ERROR_INTERNAL_ERROR,
    ERROR_INVALID_PARAMS,
    ERROR_INVALID_REQUEST,
    ERROR_METHOD_NOT_FOUND,
    ERROR_PARSE_ERROR,
    ERROR_SERVER_ERROR,
)
from jsonrpcserver.dispatcher import (
    call,
    create_request,
    dispatch_deserialized,
    dispatch_request,
    dispatch_to_response_pure,
    extract_args,
    extract_kwargs,
    extract_list,
    get_method,
    not_notification,
    to_response,
    validate_args,
    validate_request,
)
from jsonrpcserver.exceptions import JsonRpcError
from jsonrpcserver.main import (
    default_deserializer,
    default_validator,
    dispatch,
    dispatch_to_response,
)
from jsonrpcserver.methods import method
from jsonrpcserver.request import Request
from jsonrpcserver.response import (
    ErrorResponse,
    InvalidRequestResponse,
    SuccessResponse,
)
from jsonrpcserver.result import (
    ErrorResult,
    InvalidParams,
    Result,
    Success,
    SuccessResult,
)
from jsonrpcserver.sentinels import NOCONTEXT, NODATA, NOID
from jsonrpcserver.utils import identity

# pylint: disable=missing-function-docstring,missing-class-docstring,too-few-public-methods,unnecessary-lambda-assignment,invalid-name,disallowed-name


def ping() -> Result:
    return Success("pong")


# extract_list


def test_extract_list() -> None:
    assert extract_list(False, [SuccessResponse("foo", 1)]) == SuccessResponse("foo", 1)


def test_extract_list_notification() -> None:
    assert extract_list(False, [None]) is None


def test_extract_list_batch() -> None:
    assert extract_list(True, [SuccessResponse("foo", 1)]) == [
        SuccessResponse("foo", 1)
    ]


def test_extract_list_batch_all_notifications() -> None:
    assert extract_list(True, []) is None


# to_response


def test_to_response_SuccessResult() -> None:
    assert to_response(
        Request("ping", [], sentinel.id), Right(SuccessResult(sentinel.result))
    ) == Right(SuccessResponse(sentinel.result, sentinel.id))


def test_to_response_ErrorResult() -> None:
    assert (
        to_response(
            Request("ping", [], sentinel.id),
            Left(
                ErrorResult(
                    code=sentinel.code, message=sentinel.message, data=sentinel.data
                )
            ),
        )
    ) == Left(
        ErrorResponse(sentinel.code, sentinel.message, sentinel.data, sentinel.id)
    )


def test_to_response_InvalidParams() -> None:
    assert to_response(
        Request("ping", [], sentinel.id), InvalidParams(sentinel.data)
    ) == Left(ErrorResponse(-32602, "Invalid params", sentinel.data, sentinel.id))


def test_to_response_InvalidParams_no_data() -> None:
    assert to_response(Request("ping", [], sentinel.id), InvalidParams()) == Left(
        ErrorResponse(-32602, "Invalid params", NODATA, sentinel.id)
    )


def test_to_response_notification() -> None:
    with pytest.raises(AssertionError):
        to_response(Request("ping", [], NOID), SuccessResult(result=sentinel.result))


# extract_args


def test_extract_args() -> None:
    assert extract_args(Request("ping", [], NOID), NOCONTEXT) == []


def test_extract_args_with_context() -> None:
    assert extract_args(Request("ping", ["bar"], NOID), "foo") == ["foo", "bar"]


# extract_kwargs


def test_extract_kwargs() -> None:
    assert extract_kwargs(Request("ping", {"foo": "bar"}, NOID)) == {"foo": "bar"}


# validate_result


def test_validate_result_no_arguments() -> None:
    def f() -> None:
        pass

    assert validate_args(Request("f", [], NOID), NOCONTEXT, f) == Right(f)


def test_validate_result_no_arguments_too_many_positionals() -> None:
    assert validate_args(Request("f", ["foo"], NOID), NOCONTEXT, lambda: None) == Left(
        ErrorResult(
            code=ERROR_INVALID_PARAMS,
            message="Invalid params",
            data="too many positional arguments",
        )
    )


def test_validate_result_positionals() -> None:
    def f(x: Any) -> None:
        pass

    assert validate_args(Request("f", [1], NOID), NOCONTEXT, f) == Right(f)


def test_validate_result_positionals_not_passed() -> None:
    assert validate_args(
        Request("f", {"foo": "bar"}, NOID), NOCONTEXT, lambda x: None
    ) == Left(
        ErrorResult(
            ERROR_INVALID_PARAMS, "Invalid params", "missing a required argument: 'x'"
        )
    )


def test_validate_result_keywords() -> None:
    def f(**kwargs: Any) -> None:
        pass

    assert validate_args(Request("f", {"foo": "bar"}, NOID), NOCONTEXT, f) == Right(f)


def test_validate_result_object_method() -> None:
    class FooClass:
        def f(self, *_: str) -> str:
            return ""

    g = FooClass().f
    assert validate_args(Request("g", ["one", "two"], NOID), NOCONTEXT, g) == Right(g)


# call


def test_call() -> None:
    assert call(Request("ping", [], 1), NOCONTEXT, ping) == Right(SuccessResult("pong"))


def test_call_raising_jsonrpcerror() -> None:
    def method_() -> None:
        raise JsonRpcError(code=1, message="foo", data=NODATA)

    assert call(Request("ping", [], 1), NOCONTEXT, method_) == Left(
        ErrorResult(1, "foo")
    )


def test_call_raising_exception() -> None:
    """The exception message must not reach the client by default."""

    def method_() -> None:
        raise ValueError("foo")

    assert call(Request("ping", [], 1), NOCONTEXT, method_) == Left(
        ErrorResult(ERROR_INTERNAL_ERROR, "Internal error", NODATA)
    )


def test_call_raising_exception_debug() -> None:
    def method_() -> None:
        raise ValueError("foo")

    assert call(Request("ping", [], 1), NOCONTEXT, method_, debug=True) == Left(
        ErrorResult(ERROR_INTERNAL_ERROR, "Internal error", "foo")
    )


def test_call_raising_exception_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    def method_() -> None:
        raise ValueError("secret detail")

    call(Request("ping", [], 1), NOCONTEXT, method_)
    (record,) = caplog.records
    assert record.name == "jsonrpcserver.dispatcher"
    assert record.getMessage() == "Method 'ping' raised an exception"
    assert record.exc_info is not None
    assert str(record.exc_info[1]) == "secret detail"


# validate_args


@pytest.mark.parametrize(
    "argument,value",
    [
        (
            validate_args(Request("ping", [], 1), NOCONTEXT, ping),
            Right(ping),
        ),
        (
            validate_args(Request("ping", ["foo"], 1), NOCONTEXT, ping),
            Left(
                ErrorResult(
                    ERROR_INVALID_PARAMS,
                    "Invalid params",
                    "too many positional arguments",
                )
            ),
        ),
    ],
)
def test_validate_args(argument: Result, value: Result) -> None:
    assert argument == value


# get_method


@pytest.mark.parametrize(
    "argument,value",
    [
        (
            get_method({"ping": ping}, "ping"),
            Right(ping),
        ),
        (
            get_method({"ping": ping}, "non-existant"),
            Left(
                ErrorResult(ERROR_METHOD_NOT_FOUND, "Method not found", "non-existant")
            ),
        ),
    ],
)
def test_get_method(argument: Result, value: Result) -> None:
    assert argument == value


# dispatch_request


def test_dispatch_request() -> None:
    request = Request("ping", [], 1)
    assert dispatch_request({"ping": ping}, NOCONTEXT, request) == (
        request,
        Right(SuccessResult("pong")),
    )


def test_dispatch_request_with_context() -> None:
    def ping_with_context(context: Any) -> Result:
        assert context is sentinel.context
        return Success()

    dispatch_request(
        {"ping_with_context": ping_with_context},
        sentinel.context,
        Request("ping_with_context", [], 1),
    )
    # Assert is in the method


# create_request


def test_create_request() -> None:
    request = create_request({"jsonrpc": "2.0", "method": "ping"})
    assert isinstance(request, Request)


# not_notification


def test_not_notification() -> None:
    assert not_notification((Request("ping", [], 1), SuccessResult("pong"))) is True


def test_not_notification_false() -> None:
    assert not_notification((Request("ping", [], NOID), SuccessResult("pong"))) is False


# dispatch_deserialized


def test_dispatch_deserialized() -> None:
    assert dispatch_deserialized(
        methods={"ping": ping},
        context=NOCONTEXT,
        post_process=identity,
        deserialized={"jsonrpc": "2.0", "method": "ping", "id": 1},
    ) == Right(SuccessResponse("pong", 1))


# validate_request


def test_validate_request() -> None:
    request = {"jsonrpc": "2.0", "method": "ping"}
    assert validate_request(default_validator, request) == Right(request)


def test_validate_request_invalid() -> None:
    assert validate_request(default_validator, {"jsonrpc": "2.0"}) == Left(
        ErrorResponse(
            ERROR_INVALID_REQUEST,
            "Invalid request",
            "The request failed schema validation",
            None,
        )
    )


# dispatch_to_response_pure


def test_dispatch_to_response_pure() -> None:
    assert dispatch_to_response_pure(
        deserializer=default_deserializer,
        validator=default_validator,
        post_process=identity,
        context=NOCONTEXT,
        methods={"ping": ping},
        request='{"jsonrpc": "2.0", "method": "ping", "id": 1}',
    ) == Right(SuccessResponse("pong", 1))


def test_dispatch_to_response_pure_parse_error() -> None:
    """Unable to parse, must return an error"""
    assert dispatch_to_response_pure(
        deserializer=default_deserializer,
        validator=default_validator,
        post_process=identity,
        context=NOCONTEXT,
        methods={"ping": ping},
        request="{",
    ) == Left(
        ErrorResponse(
            ERROR_PARSE_ERROR,
            "Parse error",
            "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)",
            None,
        )
    )


def test_dispatch_to_response_pure_invalid_request() -> None:
    """Invalid JSON-RPC, must return an error. (impossible to determine if
    notification).
    """
    assert dispatch_to_response_pure(
        deserializer=default_deserializer,
        validator=default_validator,
        post_process=identity,
        context=NOCONTEXT,
        methods={"ping": ping},
        request="{}",
    ) == Left(
        ErrorResponse(
            ERROR_INVALID_REQUEST,
            "Invalid request",
            "The request failed schema validation",
            None,
        )
    )


def test_dispatch_to_response_pure_method_not_found() -> None:
    assert dispatch_to_response_pure(
        deserializer=default_deserializer,
        validator=default_validator,
        post_process=identity,
        context=NOCONTEXT,
        methods={},
        request='{"jsonrpc": "2.0", "method": "non_existant", "id": 1}',
    ) == Left(
        ErrorResponse(ERROR_METHOD_NOT_FOUND, "Method not found", "non_existant", 1)
    )


def test_dispatch_to_response_pure_invalid_params_auto() -> None:
    def f(colour: str, size: str) -> Result:  # pylint: disable=unused-argument
        return Success()

    assert dispatch_to_response_pure(
        deserializer=default_deserializer,
        validator=default_validator,
        post_process=identity,
        context=NOCONTEXT,
        methods={"f": f},
        request='{"jsonrpc": "2.0", "method": "f", "params": {"colour":"blue"}, "id": 1}',
    ) == Left(
        ErrorResponse(
            ERROR_INVALID_PARAMS,
            "Invalid params",
            "missing a required argument: 'size'",
            1,
        )
    )


def test_dispatch_to_response_pure_invalid_params_explicitly_returned() -> None:
    def foo(colour: str) -> Result:
        if colour not in ("orange", "red", "yellow"):
            return InvalidParams()
        return Success()

    assert dispatch_to_response_pure(
        deserializer=default_deserializer,
        validator=default_validator,
        post_process=identity,
        context=NOCONTEXT,
        methods={"foo": foo},
        request='{"jsonrpc": "2.0", "method": "foo", "params": ["blue"], "id": 1}',
    ) == Left(ErrorResponse(ERROR_INVALID_PARAMS, "Invalid params", NODATA, 1))


@pytest.mark.parametrize("debug,data", [(False, NODATA), (True, "foo")])
def test_dispatch_to_response_pure_internal_error(debug: bool, data: Any) -> None:
    def foo() -> Result:
        raise ValueError("foo")

    assert dispatch_to_response_pure(
        deserializer=default_deserializer,
        validator=default_validator,
        post_process=identity,
        context=NOCONTEXT,
        methods={"foo": foo},
        request='{"jsonrpc": "2.0", "method": "foo", "id": 1}',
        debug=debug,
    ) == Left(ErrorResponse(ERROR_INTERNAL_ERROR, "Internal error", data, 1))


@pytest.mark.parametrize("debug,data", [(False, NODATA), (True, "foo")])
@patch("jsonrpcserver.dispatcher.dispatch_request", side_effect=ValueError("foo"))
def test_dispatch_to_response_pure_server_error(
    _: Mock, debug: bool, data: Any
) -> None:
    def foo() -> Result:
        return Success()

    assert dispatch_to_response_pure(
        deserializer=default_deserializer,
        validator=default_validator,
        post_process=identity,
        context=NOCONTEXT,
        methods={"foo": foo},
        request='{"jsonrpc": "2.0", "method": "foo", "id": 1}',
        debug=debug,
    ) == Left(ErrorResponse(ERROR_SERVER_ERROR, "Server error", data, None))


def test_dispatch_to_response_pure_invalid_result() -> None:
    """Methods should return a Result, otherwise we get an Internal Error response."""

    def not_a_result() -> None:
        return None

    assert dispatch_to_response_pure(
        deserializer=default_deserializer,
        validator=default_validator,
        post_process=identity,
        context=NOCONTEXT,
        methods={"not_a_result": not_a_result},
        request='{"jsonrpc": "2.0", "method": "not_a_result", "id": 1}',
        debug=True,
    ) == Left(
        ErrorResponse(
            ERROR_INTERNAL_ERROR,
            "Internal error",
            "The method did not return a valid Result (returned None)",
            1,
        )
    )


def test_dispatch_to_response_pure_raising_exception() -> None:
    """Allow raising an exception to return an error."""

    def raise_exception() -> None:
        raise JsonRpcError(code=0, message="foo", data="bar")

    assert dispatch_to_response_pure(
        deserializer=default_deserializer,
        validator=default_validator,
        post_process=identity,
        context=NOCONTEXT,
        methods={"raise_exception": raise_exception},
        request='{"jsonrpc": "2.0", "method": "raise_exception", "id": 1}',
    ) == Left(ErrorResponse(0, "foo", "bar", 1))


# dispatch_to_response_pure -- Notifications


def test_dispatch_to_response_pure_notification() -> None:
    assert (
        dispatch_to_response_pure(
            deserializer=default_deserializer,
            validator=default_validator,
            post_process=identity,
            context=NOCONTEXT,
            methods={"ping": ping},
            request='{"jsonrpc": "2.0", "method": "ping"}',
        )
        is None
    )


def test_dispatch_to_response_pure_notification_parse_error() -> None:
    """Unable to parse, must return an error"""
    assert dispatch_to_response_pure(
        deserializer=default_deserializer,
        validator=default_validator,
        post_process=identity,
        context=NOCONTEXT,
        methods={"ping": ping},
        request="{",
    ) == Left(
        ErrorResponse(
            ERROR_PARSE_ERROR,
            "Parse error",
            "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)",
            None,
        )
    )


def test_dispatch_to_response_pure_notification_invalid_request() -> None:
    """Invalid JSON-RPC, must return an error. (impossible to determine if notification)"""
    assert dispatch_to_response_pure(
        deserializer=default_deserializer,
        validator=default_validator,
        post_process=identity,
        context=NOCONTEXT,
        methods={"ping": ping},
        request="{}",
    ) == Left(
        ErrorResponse(
            ERROR_INVALID_REQUEST,
            "Invalid request",
            "The request failed schema validation",
            None,
        )
    )


def test_dispatch_to_response_pure_notification_method_not_found() -> None:
    assert (
        dispatch_to_response_pure(
            deserializer=default_deserializer,
            validator=default_validator,
            post_process=identity,
            context=NOCONTEXT,
            methods={},
            request='{"jsonrpc": "2.0", "method": "non_existant"}',
        )
        is None
    )


def test_dispatch_to_response_pure_notification_invalid_params_auto() -> None:
    def foo(colour: str, size: str) -> Result:  # pylint: disable=unused-argument
        return Success()

    assert (
        dispatch_to_response_pure(
            deserializer=default_deserializer,
            validator=default_validator,
            post_process=identity,
            context=NOCONTEXT,
            methods={"foo": foo},
            request='{"jsonrpc": "2.0", "method": "foo", "params": {"colour":"blue"}}',
        )
        is None
    )


def test_dispatch_to_response_pure_invalid_params_notification_explicitly_returned() -> (
    None
):
    def foo(colour: str) -> Result:
        if colour not in ("orange", "red", "yellow"):
            return InvalidParams()
        return Success()

    assert (
        dispatch_to_response_pure(
            deserializer=default_deserializer,
            validator=default_validator,
            post_process=identity,
            context=NOCONTEXT,
            methods={"foo": foo},
            request='{"jsonrpc": "2.0", "method": "foo", "params": ["blue"]}',
        )
        is None
    )


def test_dispatch_to_response_pure_notification_internal_error() -> None:
    def foo(bar: str) -> Result:
        raise ValueError

    assert (
        dispatch_to_response_pure(
            deserializer=default_deserializer,
            validator=default_validator,
            post_process=identity,
            context=NOCONTEXT,
            methods={"foo": foo},
            request='{"jsonrpc": "2.0", "method": "foo"}',
        )
        is None
    )


@patch("jsonrpcserver.dispatcher.dispatch_request", side_effect=ValueError("foo"))
def test_dispatch_to_response_pure_notification_server_error(*_: Mock) -> None:
    def foo() -> Result:
        return Success()

    assert dispatch_to_response_pure(
        deserializer=default_deserializer,
        validator=default_validator,
        post_process=identity,
        context=NOCONTEXT,
        methods={"foo": foo},
        request='{"jsonrpc": "2.0", "method": "foo"}',
    ) == Left(ErrorResponse(ERROR_SERVER_ERROR, "Server error", NODATA, None))


def test_dispatch_to_response_pure_notification_invalid_result() -> None:
    """Methods should return a Result, otherwise we get an Internal Error response."""

    def not_a_result() -> None:
        return None

    assert (
        dispatch_to_response_pure(
            deserializer=default_deserializer,
            validator=default_validator,
            post_process=identity,
            context=NOCONTEXT,
            methods={"not_a_result": not_a_result},
            request='{"jsonrpc": "2.0", "method": "not_a_result"}',
        )
        is None
    )


def test_dispatch_to_response_pure_notification_raising_exception() -> None:
    """Allow raising an exception to return an error."""

    def raise_exception() -> None:
        raise JsonRpcError(code=0, message="foo", data="bar")

    assert (
        dispatch_to_response_pure(
            deserializer=default_deserializer,
            validator=default_validator,
            post_process=identity,
            context=NOCONTEXT,
            methods={"raise_exception": raise_exception},
            request='{"jsonrpc": "2.0", "method": "raise_exception"}',
        )
        is None
    )


# dispatch_to_response


def test_dispatch_to_response() -> None:
    response = dispatch_to_response(
        '{"jsonrpc": "2.0", "method": "ping", "id": 1}', {"ping": ping}
    )
    assert response == Right(SuccessResponse("pong", 1))


def test_dispatch_to_response_with_global_methods() -> None:
    @method
    def ping() -> Result:  # pylint: disable=redefined-outer-name
        return Success("ping")

    response = dispatch_to_response('{"jsonrpc": "2.0", "method": "ping", "id": 1}')
    assert response == Right(SuccessResponse("ping", 1))


# The remaining tests are direct from the examples in the specification


def test_examples_positionals() -> None:
    def subtract(minuend: int, subtrahend: int) -> Result:
        return Success(minuend - subtrahend)

    response = dispatch_to_response_pure(
        methods={"subtract": subtract},
        context=NOCONTEXT,
        validator=default_validator,
        post_process=identity,
        deserializer=default_deserializer,
        request='{"jsonrpc": "2.0", "method": "subtract", "params": [42, 23], "id": 1}',
    )
    assert response == Right(SuccessResponse(19, 1))

    # Second example
    response = dispatch_to_response_pure(
        methods={"subtract": subtract},
        context=NOCONTEXT,
        validator=default_validator,
        post_process=identity,
        deserializer=default_deserializer,
        request='{"jsonrpc": "2.0", "method": "subtract", "params": [23, 42], "id": 2}',
    )
    assert response == Right(SuccessResponse(-19, 2))


def test_examples_nameds() -> None:
    def subtract(**kwargs: int) -> Result:
        return Success(kwargs["minuend"] - kwargs["subtrahend"])

    response = dispatch_to_response_pure(
        methods={"subtract": subtract},
        context=NOCONTEXT,
        validator=default_validator,
        post_process=identity,
        deserializer=default_deserializer,
        request=(
            '{"jsonrpc": "2.0", "method": "subtract", '
            '"params": {"subtrahend": 23, "minuend": 42}, "id": 3}'
        ),
    )
    assert response == Right(SuccessResponse(19, 3))

    # Second example
    response = dispatch_to_response_pure(
        methods={"subtract": subtract},
        context=NOCONTEXT,
        validator=default_validator,
        post_process=identity,
        deserializer=default_deserializer,
        request=(
            '{"jsonrpc": "2.0", "method": "subtract", '
            '"params": {"minuend": 42, "subtrahend": 23}, "id": 4}'
        ),
    )
    assert response == Right(SuccessResponse(19, 4))


def test_examples_notification() -> None:
    response = dispatch_to_response_pure(
        methods={"update": lambda: None, "foobar": lambda: None},
        context=NOCONTEXT,
        validator=default_validator,
        post_process=identity,
        deserializer=default_deserializer,
        request='{"jsonrpc": "2.0", "method": "update", "params": [1, 2, 3, 4, 5]}',
    )
    assert response is None

    # Second example
    response = dispatch_to_response_pure(
        methods={"update": lambda: None, "foobar": lambda: None},
        context=NOCONTEXT,
        validator=default_validator,
        post_process=identity,
        deserializer=default_deserializer,
        request='{"jsonrpc": "2.0", "method": "foobar"}',
    )
    assert response is None


def test_examples_invalid_json() -> None:
    response = dispatch_to_response_pure(
        methods={"ping": ping},
        context=NOCONTEXT,
        validator=default_validator,
        post_process=identity,
        deserializer=default_deserializer,
        request=(
            '[{"jsonrpc": "2.0", "method": "sum", '
            '"params": [1,2,4], "id": "1"}, {"jsonrpc": "2.0", "method"]'
        ),
    )
    assert response == Left(
        ErrorResponse(
            ERROR_PARSE_ERROR,
            "Parse error",
            "Expecting ':' delimiter: line 1 column 96 (char 95)",
            None,
        )
    )


def test_examples_empty_array() -> None:
    # This is an invalid JSON-RPC request, should return an error.
    response = dispatch_to_response_pure(
        request="[]",
        methods={"ping": ping},
        context=NOCONTEXT,
        validator=default_validator,
        post_process=identity,
        deserializer=default_deserializer,
    )
    assert response == Left(
        ErrorResponse(
            ERROR_INVALID_REQUEST,
            "Invalid request",
            "The request failed schema validation",
            None,
        )
    )


def test_examples_invalid_jsonrpc_batch() -> None:
    response = dispatch_to_response_pure(
        deserializer=default_deserializer,
        validator=default_validator,
        post_process=identity,
        context=NOCONTEXT,
        methods={"ping": ping},
        request="[1]",
    )
    assert response == [
        Left(InvalidRequestResponse("The request failed schema validation"))
    ]


def test_examples_multiple_invalid_jsonrpc() -> None:
    response = dispatch_to_response_pure(
        deserializer=default_deserializer,
        validator=default_validator,
        post_process=identity,
        context=NOCONTEXT,
        methods={"ping": ping},
        request="[1, 2, 3]",
    )
    assert (
        response
        == [Left(InvalidRequestResponse("The request failed schema validation"))] * 3
    )


def test_examples_mixed_requests_and_notifications() -> None:
    methods: Dict[str, Callable[..., Any]] = {
        "sum": lambda *args: Success(sum(args)),
        "notify_hello": lambda *args: Success(19),
        "subtract": lambda *args: Success(args[0] - sum(args[1:])),
        "get_data": lambda: Success(["hello", 5]),
    }
    response = dispatch(
        deserializer=default_deserializer,
        validator=default_validator,
        context=NOCONTEXT,
        methods=methods,
        request="""[
            {"jsonrpc": "2.0", "method": "sum", "params": [1,2,4], "id": "1"},
            {"jsonrpc": "2.0", "method": "notify_hello", "params": [7]},
            {"jsonrpc": "2.0", "method": "subtract", "params": [42,23], "id": "2"},
            {"foo": "boo"},
            {"jsonrpc": "2.0", "method": "foo.get", "params": {"name": "myself"}, "id": "5"},
            {"jsonrpc": "2.0", "method": "get_data", "id": "9"}
        ]""",
    )
    assert json.loads(response) == [
        {"jsonrpc": "2.0", "result": 7, "id": "1"},
        {"jsonrpc": "2.0", "result": 19, "id": "2"},
        {
            "jsonrpc": "2.0",
            "error": {
                "code": ERROR_INVALID_REQUEST,
                "message": "Invalid request",
                "data": "The request failed schema validation",
            },
            "id": None,
        },
        {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": "Method not found", "data": "foo.get"},
            "id": "5",
        },
        {"jsonrpc": "2.0", "result": ["hello", 5], "id": "9"},
    ]
