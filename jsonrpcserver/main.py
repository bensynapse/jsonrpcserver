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
from importlib.resources import read_text
from typing import Any, Callable, Dict, List, Optional, Union, cast

from jsonschema.validators import validator_for

from .codes import ERROR_INTERNAL_ERROR
from .dispatcher import Deserialized, dispatch_to_response_pure, exception_data
from .methods import Methods, global_methods
from .response import Response, to_dict
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
schema = json.loads(read_text(__package__, "request-schema.json"))
klass = validator_for(schema)
klass.check_schema(schema)
default_validator = klass(schema).validate


def dispatch_to_response(
    request: str,
    methods: Optional[Methods] = None,
    *,
    context: Any = NOCONTEXT,
    deserializer: Callable[[str], Deserialized] = json.loads,
    validator: Callable[[Deserialized], object] = default_validator,
    post_process: Callable[[Response], Any] = identity,
    debug: bool = False,
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

    Returns:
        A Response, list of Responses or None.

    Examples:
       >>> dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}')
       '{"jsonrpc": "2.0", "result": "pong", "id": 1}'
    """
    return dispatch_to_response_pure(
        deserializer=deserializer,
        validator=validator,
        post_process=post_process,
        context=context,
        methods=global_methods if methods is None else methods,
        request=request,
        debug=debug,
    )


def dispatch_to_serializable(
    *args: Any, **kwargs: Any
) -> Union[Dict[str, Any], List[Dict[str, Any]], None]:
    """Takes a JSON-RPC request string and dispatches it to method(s), giving responses
    as dicts (or None).
    """
    return cast(
        Union[Dict[str, Any], List[Dict[str, Any]], None],
        dispatch_to_response(*args, post_process=to_dict, **kwargs),
    )


def dispatch_to_json(
    *args: Any,
    serializer: Callable[
        [Union[Dict[str, Any], List[Dict[str, Any]], str]], str
    ] = default_serializer,
    **kwargs: Any,
) -> str:
    """Takes a JSON-RPC request string and dispatches it to method(s), giving a JSON-RPC
    response string.

    This is the main public method, it goes through the entire JSON-RPC process - it's a
    function from JSON-RPC request string to JSON-RPC response string.

    Args:
        serializer: A function to serialize a Python object to json. The default is
            json.dumps with allow_nan=False. If it raises for a response (say the
            method returned a datetime), that response becomes an Internal error.
        The rest: Passed through to dispatch_to_serializable.
    """
    response = dispatch_to_serializable(*args, **kwargs)
    # Better to respond with the empty string instead of json "null", because "null" is
    # an invalid JSON-RPC response.
    return (
        ""
        if response is None
        else serialize(serializer, response, kwargs.get("debug", False))
    )


# "dispatch" aliases dispatch_to_json.
dispatch = dispatch_to_json
