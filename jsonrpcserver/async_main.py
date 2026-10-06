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
from .methods import Methods, global_methods
from .response import Response, to_serializable
from .sentinels import NOCONTEXT
from .utils import identity

# pylint: disable=missing-function-docstring,duplicate-code


async def dispatch_to_response(
    request: str,
    methods: Optional[Methods] = None,
    *,
    context: Any = NOCONTEXT,
    deserializer: Callable[[str], Deserialized] = default_deserializer,
    validator: Callable[[Deserialized], object] = default_validator,
    post_process: Callable[[Response], Any] = identity,
    debug: bool = False,
    max_batch_size: Optional[int] = None,
) -> Union[Response, Iterable[Response], None]:
    check_max_batch_size(max_batch_size)
    return await dispatch_to_response_pure(
        deserializer=deserializer,
        validator=validator,
        post_process=post_process,
        context=context,
        methods=global_methods if methods is None else methods,
        request=request,
        debug=debug,
        max_batch_size=max_batch_size,
    )


async def dispatch_to_serializable(
    *args: Any, **kwargs: Any
) -> Union[Dict[str, Any], List[Dict[str, Any]], None]:
    return cast(
        Union[Dict[str, Any], List[Dict[str, Any]], None],
        await dispatch_to_response(*args, post_process=to_serializable, **kwargs),
    )


async def dispatch_to_json(
    *args: Any,
    serializer: Callable[
        [Union[Dict[str, Any], List[Dict[str, Any]], None]], str
    ] = default_serializer,
    **kwargs: Any,
) -> str:
    response = await dispatch_to_serializable(*args, **kwargs)
    return (
        ""
        if response is None
        else serialize(serializer, response, kwargs.get("debug", False))
    )


dispatch = dispatch_to_json
