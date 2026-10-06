"""Dispatcher - does the hard work of this library: parses, validates and dispatches
requests, providing responses.
"""

import logging
from functools import partial
from inspect import iscoroutine, signature
from itertools import starmap
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union, cast

from oslash.either import Either, Left, Right

from .exceptions import JsonRpcError
from .methods import AnyMethod, MethodsArgument

# Importable from here in 5.0.9. The "as" form marks a re-export.
from .methods import Method as Method
from .methods import Methods as Methods
from .request import Request
from .response import (
    ErrorResponse,
    InvalidRequestResponse,
    ParseErrorResponse,
    Response,
    ServerErrorResponse,
    SuccessResponse,
)
from .result import (
    ErrorResult,
    InternalErrorResult,
    InvalidParamsResult,
    MethodNotFoundResult,
    Result,
    SuccessResult,
)
from .sentinels import NOCONTEXT, NODATA, NOID, Sentinel
from .utils import compose, identity, make_list, unwrap

Deserialized = Union[Dict[str, Any], List[Dict[str, Any]]]

logger = logging.getLogger(__name__)

# Returned by dispatch_member for a notification. Not None, because post_process may
# legitimately return None.
NORESPONSE = Sentinel("NoResponse")


def extract_list(is_batch: bool, responses: Iterable[Any]) -> Any:
    """This is the inverse of make_list. Here we extract a response back out of the list
    if it wasn't a batch request originally. Also applies a JSON-RPC rule: we do not
    respond to batches of notifications.

    Args:
        is_batch: True if the original request was a batch.
        responses: Iterable of responses.

    Returns: A single response, a batch of responses, or None (returns None to a
        notification or batch of notifications, to indicate we should not respond).
        The responses may have been through post_process, so they can be any type.
    """
    # Need to materialize the iterable here to determine if it's empty. At least we're
    # at the end of processing (also need a list, not a generator, to serialize a batch
    # response with json.dumps).
    response_list = list(responses)
    # Responses have been removed, so in the case of either a single notification or a
    # batch of only notifications, return None
    if len(response_list) == 0:
        return None
    # For batches containing at least one non-notification, return the list
    if is_batch:
        return response_list
    # For single requests, extract it back from the list (there will be only one).
    return response_list[0]


def to_response(request: Request, result: Result) -> Response:
    """Maps a Request plus a Result to a Response. A Response is just a Result plus the
    id from the original Request.

    Raises: AssertionError if the request is a notification. Notifications can't be
        responded to. If a notification is given and AssertionError is raised, we should
        respond with Server Error, because notifications should have been removed by
        this stage.

    Returns: A Response.
    """
    # Not an assert statement, because python -O would remove it.
    if request.id is NOID:
        raise AssertionError("Can't respond to a notification")
    if isinstance(result, Left):
        return Left(ErrorResponse(**result._error._asdict(), id=request.id))
    success = cast("Right[SuccessResult, ErrorResult]", result)._value
    return Right(SuccessResponse(**success._asdict(), id=request.id))


def extract_args(request: Request, context: Any) -> List[Any]:
    """Extracts the positional arguments from the request.

    If a context object is given, it's added as the first argument.

    Returns: A list containing the positional arguments.
    """
    params = request.params if isinstance(request.params, list) else []
    return [context, *params] if context is not NOCONTEXT else params


def extract_kwargs(request: Request) -> Dict[str, Any]:
    """Extracts the keyword arguments from the reqeust.

    Returns: A dict containing the keyword arguments.
    """
    return request.params if isinstance(request.params, dict) else {}


def validate_result(result: object) -> None:
    """Validate the return value from a method.

    Raises an AssertionError if the result returned from a method is invalid.

    Returns: None
    """
    # Not an assert statement, because python -O would remove it.
    error: object = getattr(result, "_error", None)
    value: object = getattr(result, "_value", None)
    if not (
        (isinstance(result, Left) and isinstance(error, ErrorResult))
        or (isinstance(result, Right) and isinstance(value, SuccessResult))
    ):
        raise AssertionError(
            f"The method did not return a valid Result (returned {result!r})"
        )


def exception_data(exc: BaseException, debug: bool) -> Any:
    """The "data" member of the error response for an unexpected exception.

    Exception messages often hold things a client must not see, like connection
    strings, file paths and SQL, so they're only included in debug mode.
    """
    return str(exc) if debug else NODATA


def call(
    request: Request, context: Any, method: AnyMethod, debug: bool = False
) -> Result:
    """Call the method.

    Handles any exceptions raised in the method, being sure to return an Error response.
    The exception is logged. Its message goes in the response only if debug is True.

    Returns: A Result.
    """
    try:
        result = method(*extract_args(request, context), **extract_kwargs(request))
        if iscoroutine(result):
            result.close()  # Avoids a "coroutine was never awaited" warning.
            raise TypeError(
                f"Method {request.method!r} is async. Use async_dispatch to call "
                "async methods."
            )
        # validate_result raises AssertionError if the return value is not a valid
        # Result, which should respond with Internal Error because its a problem in the
        # method.
        validate_result(result)
    # Raising JsonRpcError inside the method is an alternative way of returning an error
    # response.
    except JsonRpcError as exc:
        return Left(ErrorResult(code=exc.code, message=exc.message, data=exc.data))
    # Any other uncaught exception inside method - internal error.
    except Exception as exc:
        logger.exception("Method %r raised an exception", request.method)
        return Left(InternalErrorResult(exception_data(exc, debug)))
    # validate_result has checked it.
    return cast(Result, result)


def validate_args(
    request: Request, context: Any, func: AnyMethod
) -> Either[AnyMethod, ErrorResult]:
    """Ensure the method can be called with the arguments given.

    Returns: Either the function to be called, or an Invalid Params error result.
    """
    try:
        sig = signature(func)
    except ValueError:
        # Some builtins have no signature we can inspect. Call them anyway, and let
        # call() deal with a bad argument list.
        return Right(func)
    try:
        sig.bind(*extract_args(request, context), **extract_kwargs(request))
    except TypeError as exc:
        return Left(InvalidParamsResult(str(exc)))
    return Right(func)


def get_method(
    methods: MethodsArgument, method_name: str
) -> Either[AnyMethod, ErrorResult]:
    """Get the requested method from the methods dict.

    Returns: Either the function to be called, or a Method Not Found result.
    """
    try:
        return Right(methods[method_name])
    except KeyError:
        return Left(MethodNotFoundResult(method_name))


def dispatch_request(
    methods: MethodsArgument, context: Any, request: Request, debug: bool = False
) -> Tuple[Request, Result]:
    """Get the method, validates the arguments and calls the method.

    Returns: A tuple containing the Result of the method, along with the original
        Request. We need the ids from the original request to remove notifications
        before responding, and  create a Response.
    """
    return (
        request,
        get_method(methods, request.method)
        .bind(partial(validate_args, request, context))
        .bind(partial(call, request, context, debug=debug)),
    )


def create_request(request: Dict[str, Any]) -> Request:
    """Create a Request namedtuple from a dict."""
    return Request(
        request["method"], request.get("params", []), request.get("id", NOID)
    )


def not_notification(request_result: Any) -> bool:
    """True if the request was not a notification.

    Used to filter out notifications from the list of responses.
    """
    return request_result[0].id is not NOID


def dispatch_deserialized(
    methods: MethodsArgument,
    context: Any,
    post_process: Callable[[Response], Any],
    deserialized: Deserialized,
    debug: bool = False,
) -> Any:
    """This is simply continuing the pipeline from dispatch_to_response_pure. It exists
    only to be an abstraction, otherwise that function is doing too much. It continues
    on from the request string having been parsed and validated.

    Returns: A Response, a list of Responses, or None. If post_process is passed, it's
        applied to the Response(s).
    """
    results = map(
        compose(
            partial(dispatch_request, methods, context, debug=debug), create_request
        ),
        make_list(deserialized),
    )
    responses = starmap(to_response, filter(not_notification, results))
    return extract_list(isinstance(deserialized, list), map(post_process, responses))


def validate_request(
    validator: Callable[[Deserialized], object], request: Deserialized
) -> Either[Deserialized, ErrorResponse]:
    """Validate the request against a JSON-RPC schema.

    Ensures the parsed request is valid JSON-RPC.

    Returns: Either the same request passed in or an Invalid request response.
    """
    try:
        validator(request)
    # Since the validator is unknown, the specific exception that will be raised is also
    # unknown. Any exception raised we assume the request is invalid and  return an
    # "invalid request" response.
    except Exception:
        return Left(InvalidRequestResponse("The request failed schema validation"))
    return Right(request)


def deserialize_request(
    deserializer: Callable[[str], Deserialized], request: str
) -> Either[Deserialized, ErrorResponse]:
    """Parse the JSON request string.

    Returns: Either the deserialized request or a "Parse Error" response.
    """
    try:
        return Right(deserializer(request))
    # Since the deserializer is unknown, the specific exception that will be raised is
    # also unknown. Any exception raised we assume the request is invalid, return a
    # parse error response.
    except Exception as exc:
        return Left(ParseErrorResponse(str(exc)))


def dispatch_single(
    validator: Callable[[Deserialized], object],
    methods: MethodsArgument,
    context: Any,
    deserialized: Deserialized,
    debug: bool = False,
) -> Optional[Response]:
    """Validate and dispatch one member of a batch."""
    if isinstance(deserialized, list):
        return Left(InvalidRequestResponse("The request failed schema validation"))
    result = validate_request(validator, deserialized)
    if isinstance(result, Left):
        return Left(result._error)
    return cast(
        Optional[Response],
        dispatch_deserialized(methods, context, identity, unwrap(result), debug=debug),
    )


def BatchTooLargeResponse(size: int, max_batch_size: int) -> ErrorResponse:
    """The single Invalid request response for a batch over the size limit."""
    return InvalidRequestResponse(
        f"The batch has {size} requests. The limit is {max_batch_size}."
    )


def check_max_batch_size(max_batch_size: object) -> None:
    """Raise ValueError for a max_batch_size that makes no sense."""
    if max_batch_size is not None and (
        isinstance(max_batch_size, bool)
        or not isinstance(max_batch_size, int)
        or max_batch_size < 1
    ):
        raise ValueError(
            f"max_batch_size must be a positive int or None, not {max_batch_size!r}"
        )


def member_id(member: Any) -> Any:
    """The id of a batch member, or None if it has none we can use.

    Used for the error response when something unexpected goes wrong with one member
    of a batch.
    """
    if isinstance(member, dict):
        id_ = cast(Dict[str, Any], member).get("id")
        if id_ is None or isinstance(id_, (str, int, float)):
            return id_
    return None


def dispatch_member(
    validator: Callable[[Deserialized], object],
    methods: MethodsArgument,
    context: Any,
    post_process: Callable[[Response], Any],
    member: Any,
    debug: bool = False,
) -> Any:
    """Dispatch one member of a batch, keeping any failure inside that member.

    Returns: The post-processed response, or NORESPONSE for a notification.
    """
    response: Optional[Response]
    try:
        response = dispatch_single(validator, methods, context, member, debug=debug)
    except Exception as exc:
        logger.exception("Error while dispatching a member of a batch")
        response = Left(
            ServerErrorResponse(exception_data(exc, debug), member_id(member))
        )
    return NORESPONSE if response is None else post_process(response)


def dispatch_to_response_pure(
    *,
    deserializer: Callable[[str], Deserialized],
    validator: Callable[[Deserialized], object],
    methods: MethodsArgument,
    context: Any,
    post_process: Callable[[Response], Any],
    request: str,
    debug: bool = False,
    max_batch_size: Optional[int] = None,
) -> Any:
    """A function from JSON-RPC request string to Response namedtuple(s), (yet to be
    serialized to json).

    If debug is True, error responses for unexpected exceptions include the exception
    message in "data". Leave it off in production.

    If max_batch_size is given, a batch with more members than that gets a single
    Invalid request response, and none of its members are dispatched.

    Returns: A single Response, a list of Responses, or None, each passed through
        post_process. None is given for notifications or batches of notifications, to
        indicate that we should not respond.
    """
    try:
        parsed = deserialize_request(deserializer, request)
        if isinstance(parsed, Left):
            return post_process(Left(parsed._error))
        deserialized = unwrap(parsed)
        if isinstance(deserialized, list) and deserialized:
            if max_batch_size is not None and len(deserialized) > max_batch_size:
                return post_process(
                    Left(BatchTooLargeResponse(len(deserialized), max_batch_size))
                )
            responses = [
                dispatch_member(
                    validator, methods, context, post_process, member, debug=debug
                )
                for member in deserialized
            ]
            return extract_list(
                True, [response for response in responses if response is not NORESPONSE]
            )
        validated = validate_request(validator, deserialized)
        if isinstance(validated, Left):
            return post_process(Left(validated._error))
        return dispatch_deserialized(
            methods, context, post_process, unwrap(validated), debug=debug
        )
    except Exception as exc:
        # There was an error with the jsonrpcserver library.
        logger.exception("Error while dispatching the request")
        return post_process(Left(ServerErrorResponse(exception_data(exc, debug), None)))
