"""The public functions.

These three public functions all perform the same function of dispatching a JSON-RPC
request, but they each give a different return value.

- dispatch_to_responses: Returns Response(s) (or None for notifications).
- dispatch_to_serializable: Returns a Python dict or list of dicts (or None for
  notifications).
- dispatch_to_json/dispatch: Returns a JSON-RPC response string (or an empty string for
  notifications).
"""

import json
import logging
import pkgutil
from typing import Any, Callable, Dict, List, Optional, Union, cast

from jsonschema.validators import validator_for

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
from .response import (
    # Importable from here in 5.0.9. The "as" form marks it as a re-export.
    to_serializable_one as to_serializable_one,
)
from .sentinels import NOCONTEXT, NODATA
from .utils import identity

logger = logging.getLogger(__name__)

default_deserializer = json.loads


def default_serializer(response: Any) -> str:
    """json.dumps, but NaN and Infinity raise ValueError instead of producing output
    that isn't valid JSON.
    """
    return json.dumps(response, allow_nan=False)


def serialize_one(
    serializer: Callable[[Any], str], response: Dict[str, Any], debug: bool
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
        error: Dict[str, Any] = {
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
    response: Union[Dict[str, Any], List[Dict[str, Any]]],
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


# Prepare the jsonschema validator. This is global so it loads only once, not every
# time dispatch is called.
# pkgutil.get_data works on every supported Python, and inside zip files and frozen
# apps. importlib.resources.read_text is deprecated on 3.11 and 3.12.
schema = json.loads(
    pkgutil.get_data(__name__.rpartition(".")[0], "request-schema.json") or b""
)
klass = validator_for(schema)
klass.check_schema(schema)
default_validator = klass(schema).validate


def dispatch_to_response(
    request: str,
    methods: Optional[MethodsArgument] = None,
    *,
    context: Any = NOCONTEXT,
    deserializer: Callable[[str], Deserialized] = json.loads,
    validator: Callable[[Deserialized], object] = default_validator,
    post_process: Callable[[Response], Any] = identity,
    debug: bool = False,
    max_batch_size: Optional[int] = None,
) -> Union[Response, List[Response], None]:
    """Takes a JSON-RPC request string and dispatches it to method(s), giving Response
    namedtuple(s) or None.

    This is a public wrapper around dispatch_to_response_pure, adding globals and
    default values to be nicer for end users.

    Args:
        request: The JSON-RPC request string.
        methods: Dictionary of methods that can be called - mapping of function names to
            functions. If not passed, uses the internal global_methods dict which is
            populated with the @method decorator.
        context: If given, will be passed as the first argument to methods.
        deserializer: Function that deserializes the request string.
        validator: Function that validates the JSON-RPC request. The function should
            raise an exception if the request is invalid. Batch members are validated
            individually, with nested arrays rejected before calling the validator.
            To disable validation, pass lambda _: None.
        post_process: Function that will be applied to Responses.
        debug: If True, the error response for an uncaught exception in a method
            includes the exception message in "data". The default leaves "data" out,
            because exception messages can contain passwords, file paths and other
            details a client shouldn't see. Only turn this on in development. The
            exception is logged either way.
        max_batch_size: The most requests a batch may hold. A bigger batch gets a
            single Invalid request response and none of it is dispatched. The default,
            None, means no limit. Every member costs validation time, so a server
            open to the internet should set one, such as 100.

    Returns:
        A Response, list of Responses or None.

    Examples:
       >>> dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}')
       '{"jsonrpc": "2.0", "result": "pong", "id": 1}'
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
    return cast(Union[Response, List[Response], None], response)


def dispatch_to_serializable(
    request: str,
    methods: Optional[MethodsArgument] = None,
    *,
    context: Any = NOCONTEXT,
    deserializer: Callable[[str], Deserialized] = default_deserializer,
    validator: Callable[[Deserialized], object] = default_validator,
    debug: bool = False,
    max_batch_size: Optional[int] = None,
) -> Union[Dict[str, Any], List[Dict[str, Any]], None]:
    """Takes a JSON-RPC request string and dispatches it to method(s), giving responses
    as dicts (or None).

    The arguments are the same as dispatch_to_response, apart from post_process.
    """
    return cast(
        Union[Dict[str, Any], List[Dict[str, Any]], None],
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
    methods: Optional[MethodsArgument] = None,
    *,
    context: Any = NOCONTEXT,
    deserializer: Callable[[str], Deserialized] = default_deserializer,
    validator: Callable[[Deserialized], object] = default_validator,
    debug: bool = False,
    max_batch_size: Optional[int] = None,
    serializer: Callable[
        [Union[Dict[str, Any], List[Dict[str, Any]], str]], str
    ] = default_serializer,
) -> str:
    """Takes a JSON-RPC request string and dispatches it to method(s), giving a JSON-RPC
    response string.

    This is the main public method, it goes through the entire JSON-RPC process - it's a
    function from JSON-RPC request string to JSON-RPC response string.

    Args:
        serializer: A function to serialize a Python object to json. The default is
            json.dumps with allow_nan=False. If it raises for a response (say the
            method returned a datetime), that response becomes an Internal error.
        The rest: The same as dispatch_to_response.
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


# "dispatch" aliases dispatch_to_json.
dispatch = dispatch_to_json
