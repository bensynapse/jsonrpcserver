"""Async version of dispatcher.py"""

import asyncio
import logging
from functools import partial
from inspect import isawaitable
from itertools import starmap
from typing import Any, Callable, Iterable, Optional, Tuple, Union

from oslash.either import Left  # type: ignore

from .dispatcher import (
    NORESPONSE,
    BatchTooLargeResponse,
    Deserialized,
    create_request,
    deserialize_request,
    exception_data,
    extract_args,
    extract_kwargs,
    extract_list,
    get_method,
    member_id,
    not_notification,
    to_response,
    validate_args,
    validate_request,
    validate_result,
)
from .exceptions import JsonRpcError
from .methods import Method, Methods
from .request import Request
from .response import InvalidRequestResponse, Response, ServerErrorResponse
from .result import ErrorResult, InternalErrorResult, Result
from .utils import identity, make_list

logger = logging.getLogger(__name__)


async def call(
    request: Request, context: Any, method: Method, debug: bool = False
) -> Result:
    try:
        result = method(*extract_args(request, context), **extract_kwargs(request))
        # Plain (sync) methods work too. Their result is used as it is.
        if isawaitable(result):
            result = await result
        validate_result(result)
    except JsonRpcError as exc:
        return Left(ErrorResult(code=exc.code, message=exc.message, data=exc.data))
    except Exception as exc:
        # Other error inside method - Internal error
        logger.exception("Method %r raised an exception", request.method)
        return Left(InternalErrorResult(exception_data(exc, debug)))
    return result


async def dispatch_request(
    methods: Methods, context: Any, request: Request, debug: bool = False
) -> Tuple[Request, Result]:
    method = get_method(methods, request.method).bind(
        partial(validate_args, request, context)
    )
    return (
        request,
        method
        if isinstance(method, Left)
        else await call(request, context, method._value, debug=debug),
    )


async def dispatch_deserialized(
    methods: Methods,
    context: Any,
    post_process: Callable[[Response], Iterable[Any]],
    deserialized: Deserialized,
    debug: bool = False,
) -> Union[Response, Iterable[Response], None]:
    results = await asyncio.gather(
        *(
            dispatch_request(methods, context, r, debug=debug)
            for r in map(create_request, make_list(deserialized))
        )
    )
    return extract_list(
        isinstance(deserialized, list),
        map(
            post_process,
            starmap(to_response, filter(not_notification, results)),
        ),
    )


async def dispatch_single(
    validator: Callable[[Deserialized], object],
    methods: Methods,
    context: Any,
    deserialized: Deserialized,
    debug: bool = False,
) -> Union[Response, None]:
    """Validate and dispatch one member of a batch."""
    result = (
        Left(InvalidRequestResponse("The request failed schema validation"))
        if isinstance(deserialized, list)
        else validate_request(validator, deserialized)
    )
    return (
        result
        if isinstance(result, Left)
        else await dispatch_deserialized(
            methods, context, identity, result._value, debug=debug
        )
    )


async def dispatch_member(
    validator: Callable[[Deserialized], object],
    methods: Methods,
    context: Any,
    post_process: Callable[[Response], Any],
    member: Any,
    debug: bool = False,
) -> Any:
    """Dispatch one member of a batch, keeping any failure inside that member.

    Returns: The post-processed response, or NORESPONSE for a notification.
    """
    try:
        response = await dispatch_single(
            validator, methods, context, member, debug=debug
        )
    except Exception as exc:
        logger.exception("Error while dispatching a member of a batch")
        response = Left(
            ServerErrorResponse(exception_data(exc, debug), member_id(member))
        )
    return NORESPONSE if response is None else post_process(response)


async def dispatch_to_response_pure(
    *,
    deserializer: Callable[[str], Deserialized],
    validator: Callable[[Deserialized], object],
    methods: Methods,
    context: Any,
    post_process: Callable[[Response], Iterable[Any]],
    request: str,
    debug: bool = False,
    max_batch_size: Optional[int] = None,
) -> Union[Response, Iterable[Response], None]:
    try:
        result = deserialize_request(deserializer, request)
        if (
            not isinstance(result, Left)
            and isinstance(result._value, list)
            and result._value
        ):
            if max_batch_size is not None and len(result._value) > max_batch_size:
                return post_process(
                    Left(BatchTooLargeResponse(len(result._value), max_batch_size))
                )
            responses = await asyncio.gather(
                *(
                    dispatch_member(
                        validator, methods, context, post_process, member, debug=debug
                    )
                    for member in result._value
                )
            )
            return extract_list(
                True, [response for response in responses if response is not NORESPONSE]
            )
        result = result.bind(partial(validate_request, validator))
        return (
            post_process(result)
            if isinstance(result, Left)
            else await dispatch_deserialized(
                methods, context, post_process, result._value, debug=debug
            )
        )
    except Exception as exc:
        logger.exception("Error while dispatching the request")
        return post_process(Left(ServerErrorResponse(exception_data(exc, debug), None)))
