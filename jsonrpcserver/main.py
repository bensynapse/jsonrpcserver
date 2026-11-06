"""The dispatch functions.

All three take a JSON-RPC request string, call the methods and give the response.
They differ only in the form of the response:

- dispatch_to_response gives Response objects, or None for a notification.
- dispatch_to_serializable gives a dict or a list of dicts, or None for a
  notification.
- dispatch_to_json, also called dispatch, gives a JSON string, or an empty string
  for a notification.
"""

import json
import logging
import math
from collections.abc import Callable
from typing import Any, cast

from .codes import ERROR_INTERNAL_ERROR
from .dispatcher import (
    Deserialized,
    check_max_batch_size,
    dispatch_to_response_pure,
    exception_data,
)

# Importable from here in 5.0.9. The "as" form marks a re-export.
from .methods import Methods as Methods
from .methods import MethodsArgument, global_methods
from .response import (
    Response,
    to_dict,
)
from .sentinels import NOCONTEXT, NODATA
from .utils import identity
from .validator import default_validator as default_validator

logger = logging.getLogger(__name__)

DEFAULT_MAX_BATCH_SIZE = 100
"""The default for `max_batch_size`: the most requests a batch may hold. New in 6.0,
which turned the limit on by default. Pass `max_batch_size=None` to turn it off."""


def _reject_constant(constant: str) -> Any:
    raise ValueError(f"{constant} is not valid JSON")


def _finite_float(text: str) -> float:
    number = float(text)
    if math.isinf(number):
        raise ValueError(f"{text} is too big")
    return number


def default_deserializer(request: str) -> Any:
    """json.loads, but `NaN`, `Infinity`, `-Infinity` and numbers too big for a float
    raise ValueError, which the client gets as a -32700 Parse error.

    They aren't valid JSON (RFC 8259, section 6). New in 6.0: 5.x accepted them.
    """
    return json.loads(
        request, parse_constant=_reject_constant, parse_float=_finite_float
    )


def default_serializer(response: Any) -> str:
    """json.dumps, but NaN and Infinity raise ValueError instead of producing output
    that isn't valid JSON.
    """
    return json.dumps(response, allow_nan=False)


def serialize_one(
    serializer: Callable[[Any], str], response: dict[str, Any], debug: bool
) -> str:
    """Serialize one response. If that fails, serialize an Internal error for the same
    request instead, so the client still gets a valid JSON-RPC response.
    """
    try:
        return serializer(response)
    except Exception as exc:
        logger.exception(
            "Could not serialize the response for request id %r", response.get("id")
        )
        data = exception_data(exc, debug)
        error: dict[str, Any] = {
            "jsonrpc": "2.0",
            "error": {
                "code": ERROR_INTERNAL_ERROR,
                "message": "Internal error",
                **({} if data is NODATA else {"data": data}),
            },
            "id": response.get("id"),
        }
        try:
            return serializer(error)
        except Exception:
            # The id itself can't be serialized (for example it was 1e400, which
            # json.loads reads as infinity).
            error["id"] = None
            return json.dumps(error)


def serialize(
    serializer: Callable[[Any], str],
    response: dict[str, Any] | list[dict[str, Any]],
    debug: bool,
) -> str:
    """Serialize a response or batch of responses.

    A response that can't be serialized becomes an Internal error response. In a batch,
    the other responses are kept.
    """
    try:
        return serializer(response)
    except Exception:
        if isinstance(response, list):
            return (
                "["
                + ", ".join(serialize_one(serializer, r, debug) for r in response)
                + "]"
            )
        return serialize_one(serializer, response, debug)


def dispatch_to_response(
    request: str,
    methods: MethodsArgument | None = None,
    *,
    context: Any = NOCONTEXT,
    deserializer: Callable[[str], Deserialized] = default_deserializer,
    validator: Callable[[Deserialized], object] = default_validator,
    post_process: Callable[[Response], Any] = identity,
    debug: bool = False,
    max_batch_size: int | None = DEFAULT_MAX_BATCH_SIZE,
) -> Response | list[Response] | None:
    """Dispatch a request and give the response as Response objects.

    Most code wants `dispatch` (a JSON string) or `dispatch_to_serializable` (dicts)
    instead. Use this one to inspect or change responses before they're serialized.

    Each Response is a `SuccessResponse` or an `ErrorResponse`, frozen dataclasses
    with the response's fields. Check `isinstance(response, ErrorResponse)` to tell
    them apart. Changed in 6.0: 5.x wrapped them in oslash's `Right` and `Left`.

    Args:
        request: The JSON-RPC request string.
        methods: The methods requests can call, as a dict (or any mapping) of names
            to functions. The default is the dict that `@method` fills in,
            `jsonrpcserver.methods.global_methods`.
        context: If given, it's passed as the first argument to every method. The
            client can't see or set it.
        deserializer: The function that parses the request string. The default,
            `default_deserializer`, is `json.loads` that also rejects `NaN`,
            `Infinity` and numbers too big for a float (changed in 6.0). If it
            raises, the client gets a -32700 Parse error whose `data` is the
            exception message.
        validator: The function that checks a parsed request against the JSON-RPC
            spec. It should raise an exception, of any kind, if the request is
            invalid. In a batch it's called once for each request (new in 5.0.10).
            The default checks the JSON-RPC 2.0 rules (`jsonrpcserver.validator`).
            `lambda _: None` turns validation off.
        post_process: A function applied to each Response before it's returned.
        debug: If True, the error response for an exception a method doesn't catch
            includes the exception message in `data`. The default leaves `data`
            out, because exception messages can contain passwords, file paths and
            other details a client shouldn't see. The exception is logged either
            way. New in 5.0.10.
        max_batch_size: The most requests a batch may hold. A bigger batch gets a
            single -32600 Invalid request response, and none of it is run. The
            default is 100 (`DEFAULT_MAX_BATCH_SIZE`). None means no limit. New in
            5.0.10. Changed in 6.0: 5.x had no limit by default.

    Returns:
        A Response for a single request, a list of Responses for a batch, or None
            if there's nothing to send back (a notification, or a batch of only
            notifications). With `post_process`, whatever it returns for each.

    Raises:
        ValueError: If `max_batch_size` isn't None or a positive int. Requests never
            raise: a bad request or a failing method gives an error response.
    """
    check_max_batch_size(max_batch_size)
    response = dispatch_to_response_pure(
        deserializer=deserializer,
        validator=validator,
        post_process=post_process,
        context=context,
        methods=global_methods if methods is None else methods,
        request=request,
        debug=debug,
        max_batch_size=max_batch_size,
    )
    return cast(Response | list[Response] | None, response)


def dispatch_to_serializable(
    request: str,
    methods: MethodsArgument | None = None,
    *,
    context: Any = NOCONTEXT,
    deserializer: Callable[[str], Deserialized] = default_deserializer,
    validator: Callable[[Deserialized], object] = default_validator,
    debug: bool = False,
    max_batch_size: int | None = DEFAULT_MAX_BATCH_SIZE,
) -> dict[str, Any] | list[dict[str, Any]] | None:
    """Dispatch a request and give the response as a dict.

    Use it when your framework serializes the response itself, such as a Django
    `JsonResponse`, or when you want to inspect it.

    Args:
        request: The JSON-RPC request string.
        methods: The same as for `dispatch_to_response`.
        context: The same as for `dispatch_to_response`.
        deserializer: The same as for `dispatch_to_response`.
        validator: The same as for `dispatch_to_response`.
        debug: The same as for `dispatch_to_response`.
        max_batch_size: The same as for `dispatch_to_response`.

    Returns:
        The response as a dict, a list of dicts for a batch, or None if there's
            nothing to send back.

    Raises:
        ValueError: If `max_batch_size` isn't None or a positive int.

    Example:
        >>> from jsonrpcserver import Result, Success, dispatch_to_serializable
        >>> def ping() -> Result:
        ...     return Success("pong")
        >>> dispatch_to_serializable(
        ...     '{"jsonrpc": "2.0", "method": "ping", "id": 1}', methods={"ping": ping}
        ... )
        {'jsonrpc': '2.0', 'result': 'pong', 'id': 1}
    """
    return cast(
        dict[str, Any] | list[dict[str, Any]] | None,
        dispatch_to_response(
            request,
            methods,
            context=context,
            deserializer=deserializer,
            validator=validator,
            debug=debug,
            max_batch_size=max_batch_size,
            post_process=to_dict,
        ),
    )


def dispatch_to_json(
    request: str,
    methods: MethodsArgument | None = None,
    *,
    context: Any = NOCONTEXT,
    deserializer: Callable[[str], Deserialized] = default_deserializer,
    validator: Callable[[Deserialized], object] = default_validator,
    debug: bool = False,
    max_batch_size: int | None = DEFAULT_MAX_BATCH_SIZE,
    serializer: Callable[
        [dict[str, Any] | list[dict[str, Any]] | str], str
    ] = default_serializer,
) -> str:
    """Dispatch a request and give the response as a JSON string.

    This is `dispatch`, the function most code uses. Send the string back to the
    client. An empty string means there's nothing to send back: the request was a
    notification, or a batch of only notifications. Over HTTP, send status 204 with
    no body for that.

    Args:
        request: The JSON-RPC request string.
        methods: The same as for `dispatch_to_response`.
        context: The same as for `dispatch_to_response`.
        deserializer: The same as for `dispatch_to_response`.
        validator: The same as for `dispatch_to_response`.
        debug: The same as for `dispatch_to_response`.
        max_batch_size: The same as for `dispatch_to_response`.
        serializer: The function that turns the response into a string. The
            default is `json.dumps` with `allow_nan=False`, so a result holding NaN
            or Infinity gives an Internal error instead of invalid JSON (new in
            5.0.10). If the serializer raises for a response, say because the
            method returned a `datetime`, that response becomes an Internal error
            and the rest of a batch is sent as usual.

    Returns:
        The response as a JSON string, or "" if there's nothing to send back.

    Raises:
        ValueError: If `max_batch_size` isn't None or a positive int.

    Example:
        >>> from jsonrpcserver import Result, Success, dispatch
        >>> def ping() -> Result:
        ...     return Success("pong")
        >>> dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}', {"ping": ping})
        '{"jsonrpc": "2.0", "result": "pong", "id": 1}'
    """
    response = dispatch_to_serializable(
        request,
        methods,
        context=context,
        deserializer=deserializer,
        validator=validator,
        debug=debug,
        max_batch_size=max_batch_size,
    )
    # Better to respond with the empty string instead of json "null", because "null" is
    # an invalid JSON-RPC response.
    return "" if response is None else serialize(serializer, response, debug)


dispatch = dispatch_to_json
"""Another name for `dispatch_to_json`, and the one most code uses."""
