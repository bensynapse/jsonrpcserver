"""The async dispatch functions, for asyncio servers.

They take the same arguments as the functions in main.py, and are imported from
the package as async_dispatch, async_dispatch_to_serializable and
async_dispatch_to_response. Methods can be async functions or plain ones. The
requests in a batch run concurrently.
"""

from typing import Any, Callable, Dict, Iterable, List, Optional, Union, cast

from .async_dispatcher import dispatch_to_response_pure
from .dispatcher import Deserialized, check_max_batch_size
from .main import (
    default_deserializer,
    default_serializer,
    default_validator,
    serialize,
)

# Importable from here in 5.0.9. The "as" form marks a re-export.
from .methods import Methods as Methods
from .methods import MethodsArgument, global_methods
from .response import Response, to_serializable
from .sentinels import NOCONTEXT
from .utils import identity


async def dispatch_to_response(
    request: str,
    methods: Optional[MethodsArgument] = None,
    *,
    context: Any = NOCONTEXT,
    deserializer: Callable[[str], Deserialized] = default_deserializer,
    validator: Callable[[Deserialized], object] = default_validator,
    post_process: Callable[[Response], Any] = identity,
    debug: bool = False,
    max_batch_size: Optional[int] = None,
) -> Union[Response, Iterable[Response], None]:
    """Dispatch a request and give the response as Response objects. Async.

    The async version of `dispatch_to_response`, imported from the package as
    `async_dispatch_to_response`. It takes the same arguments.

    Args:
        request: The JSON-RPC request string.
        methods: The same as for `dispatch_to_response`.
        context: The same as for `dispatch_to_response`.
        deserializer: The same as for `dispatch_to_response`.
        validator: The same as for `dispatch_to_response`.
        post_process: The same as for `dispatch_to_response`.
        debug: The same as for `dispatch_to_response`.
        max_batch_size: The same as for `dispatch_to_response`. Every request in a
            batch runs at the same time, so a limit matters even more here.

    Returns:
        A Response for a single request, a list of Responses for a batch, or None
            if there's nothing to send back. The type hint says Iterable for a
            batch, but it's a list.

    Raises:
        ValueError: If `max_batch_size` isn't None or a positive int.
    """
    check_max_batch_size(max_batch_size)
    response = await dispatch_to_response_pure(
        deserializer=deserializer,
        validator=validator,
        post_process=post_process,
        context=context,
        methods=global_methods if methods is None else methods,
        request=request,
        debug=debug,
        max_batch_size=max_batch_size,
    )
    return cast(Union[Response, Iterable[Response], None], response)


async def dispatch_to_serializable(
    request: str,
    methods: Optional[MethodsArgument] = None,
    *,
    context: Any = NOCONTEXT,
    deserializer: Callable[[str], Deserialized] = default_deserializer,
    validator: Callable[[Deserialized], object] = default_validator,
    debug: bool = False,
    max_batch_size: Optional[int] = None,
) -> Union[Dict[str, Any], List[Dict[str, Any]], None]:
    """Dispatch a request and give the response as a dict. Async.

    The async version of `dispatch_to_serializable`, imported from the package as
    `async_dispatch_to_serializable`.

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
    """
    return cast(
        Union[Dict[str, Any], List[Dict[str, Any]], None],
        await dispatch_to_response(
            request,
            methods,
            context=context,
            deserializer=deserializer,
            validator=validator,
            debug=debug,
            max_batch_size=max_batch_size,
            post_process=to_serializable,
        ),
    )


async def dispatch_to_json(
    request: str,
    methods: Optional[MethodsArgument] = None,
    *,
    context: Any = NOCONTEXT,
    deserializer: Callable[[str], Deserialized] = default_deserializer,
    validator: Callable[[Deserialized], object] = default_validator,
    debug: bool = False,
    max_batch_size: Optional[int] = None,
    serializer: Callable[
        [Union[Dict[str, Any], List[Dict[str, Any]], None]], str
    ] = default_serializer,
) -> str:
    """Dispatch a request and give the response as a JSON string. Async.

    This is `async_dispatch`, the async version of `dispatch`. Methods can be async
    functions or plain ones (plain ones work from 5.0.10). A plain method runs on
    the event loop, so a slow one holds up every other request.

    Args:
        request: The JSON-RPC request string.
        methods: The same as for `dispatch_to_response`.
        context: The same as for `dispatch_to_response`.
        deserializer: The same as for `dispatch_to_response`.
        validator: The same as for `dispatch_to_response`.
        debug: The same as for `dispatch_to_response`.
        max_batch_size: The same as for `dispatch_to_response`.
        serializer: The same as for `dispatch`.

    Returns:
        The response as a JSON string, or "" if there's nothing to send back.

    Raises:
        ValueError: If `max_batch_size` isn't None or a positive int.

    Example:
        >>> import asyncio
        >>> from jsonrpcserver import Result, Success, async_dispatch
        >>> async def ping() -> Result:
        ...     return Success("pong")
        >>> request = '{"jsonrpc": "2.0", "method": "ping", "id": 1}'
        >>> asyncio.run(async_dispatch(request, {"ping": ping}))
        '{"jsonrpc": "2.0", "result": "pong", "id": 1}'
    """
    response = await dispatch_to_serializable(
        request,
        methods,
        context=context,
        deserializer=deserializer,
        validator=validator,
        debug=debug,
        max_batch_size=max_batch_size,
    )
    return "" if response is None else serialize(serializer, response, debug)


dispatch = dispatch_to_json
"""Another name for `dispatch_to_json`. The package exports it as `async_dispatch`."""
