"""Async version of dispatcher.py"""

import asyncio
import logging
from collections.abc import Callable
from inspect import isawaitable
from itertools import starmap
from typing import Any, cast

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
    to_result,
    validate_args,
    validate_request,
)
from .exceptions import JsonRpcError
from .methods import AnyMethod, MethodsArgument

# Importable from here in 5.0.9. The "as" form marks a re-export.
from .methods import Method as Method
from .methods import Methods as Methods
from .request import Request
from .response import (
    ErrorResponse,
    InvalidRequestResponse,
    Response,
    ServerErrorResponse,
)
from .result import ErrorResult, InternalErrorResult, Result
from .utils import identity, make_list

logger = logging.getLogger(__name__)


async def call(
    request: Request, context: Any, method: AnyMethod, debug: bool = False
) -> Result:
    try:
        result = method(*extract_args(request, context), **extract_kwargs(request))
        # Plain (sync) methods work too. Their result is used as it is.
        if isawaitable(result):
            result = await result
    except JsonRpcError as exc:
        return ErrorResult(code=exc.code, message=exc.message, data=exc.data)
    except Exception as exc:
        # Other error inside method - Internal error
        logger.exception("Method %r raised an exception", request.method)
        return InternalErrorResult(exception_data(exc, debug))
    # A plain value becomes Success(value) (5.1.0).
    return to_result(result)


async def dispatch_request(
    methods: MethodsArgument, context: Any, request: Request, debug: bool = False
) -> tuple[Request, Result]:
    method = get_method(methods, request.method)
    if isinstance(method, ErrorResult):
        return request, method
    checked = validate_args(request, context, method)
    if isinstance(checked, ErrorResult):
        return request, checked
    return request, await call(request, context, checked, debug=debug)


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
) -> Response | None:
    """Validate and dispatch one member of a batch."""
    if isinstance(deserialized, list):
        return InvalidRequestResponse("The request failed schema validation")
    result = validate_request(validator, deserialized)
    if isinstance(result, ErrorResponse):
        return result
    return cast(
        Response | None,
        await dispatch_deserialized(methods, context, identity, result, debug=debug),
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
    response: Response | None
    try:
        response = await dispatch_single(
            validator, methods, context, member, debug=debug
        )
    except Exception as exc:
        logger.exception("Error while dispatching a member of a batch")
        response = ServerErrorResponse(exception_data(exc, debug), member_id(member))
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
    max_batch_size: int | None = None,
) -> Any:
    try:
        parsed = deserialize_request(deserializer, request)
        if isinstance(parsed, ErrorResponse):
            return post_process(parsed)
        deserialized = parsed
        if isinstance(deserialized, list) and deserialized:
            if max_batch_size is not None and len(deserialized) > max_batch_size:
                return post_process(
                    BatchTooLargeResponse(len(deserialized), max_batch_size)
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
        if isinstance(validated, ErrorResponse):
            return post_process(validated)
        return await dispatch_deserialized(
            methods, context, post_process, validated, debug=debug
        )
    except Exception as exc:
        logger.exception("Error while dispatching the request")
        return post_process(ServerErrorResponse(exception_data(exc, debug), None))
