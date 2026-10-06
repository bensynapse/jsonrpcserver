"""Async version of dispatcher.py"""

import asyncio
import logging
from functools import partial
from inspect import isawaitable
from itertools import starmap
from typing import Any, Callable, Optional, Tuple, cast

from oslash.either import Left

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
from .methods import AnyMethod, MethodsArgument

# Importable from here in 5.0.9. The "as" form marks a re-export.
from .methods import Method as Method
from .methods import Methods as Methods
from .request import Request
from .response import InvalidRequestResponse, Response, ServerErrorResponse
from .result import ErrorResult, InternalErrorResult, Result
from .utils import identity, make_list, unwrap

logger = logging.getLogger(__name__)


async def call(
    request: Request, context: Any, method: AnyMethod, debug: bool = False
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
    # validate_result has checked it.
    return cast(Result, result)


async def dispatch_request(
    methods: MethodsArgument, context: Any, request: Request, debug: bool = False
) -> Tuple[Request, Result]:
    method = get_method(methods, request.method).bind(
        partial(validate_args, request, context)
    )
    if isinstance(method, Left):
        return request, cast(Result, method)
    return request, await call(request, context, unwrap(method), debug=debug)


async def dispatch_deserialized(
    methods: MethodsArgument,
    context: Any,
    post_process: Callable[[Response], Any],
    deserialized: Deserialized,
    debug: bool = False,
) -> Any:
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
        await dispatch_deserialized(
            methods, context, identity, unwrap(result), debug=debug
        ),
    )


async def dispatch_member(
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
    methods: MethodsArgument,
    context: Any,
    post_process: Callable[[Response], Any],
    request: str,
    debug: bool = False,
    max_batch_size: Optional[int] = None,
) -> Any:
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
            responses = await asyncio.gather(
                *(
                    dispatch_member(
                        validator, methods, context, post_process, member, debug=debug
                    )
                    for member in deserialized
                )
            )
            return extract_list(
                True, [response for response in responses if response is not NORESPONSE]
            )
        validated = validate_request(validator, deserialized)
        if isinstance(validated, Left):
            return post_process(Left(validated._error))
        return await dispatch_deserialized(
            methods, context, post_process, unwrap(validated), debug=debug
        )
    except Exception as exc:
        logger.exception("Error while dispatching the request")
        return post_process(Left(ServerErrorResponse(exception_data(exc, debug), None)))
