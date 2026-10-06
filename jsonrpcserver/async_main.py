"""Async version of main.py. The public async functions."""

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
