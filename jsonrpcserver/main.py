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
from importlib.resources import read_text
from typing import Any, Callable, Dict, List, Optional, Union, cast

from jsonschema.validators import validator_for  # type: ignore

from .dispatcher import Deserialized, dispatch_to_response_pure
from .methods import Methods, global_methods
from .response import Response, to_dict
from .sentinels import NOCONTEXT
from .utils import identity

default_deserializer = json.loads

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
    validator: Callable[[Deserialized], Deserialized] = default_validator,
    post_process: Callable[[Response], Any] = identity,
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
    ] = json.dumps,
    **kwargs: Any,
) -> str:
    """Takes a JSON-RPC request string and dispatches it to method(s), giving a JSON-RPC
    response string.

    This is the main public method, it goes through the entire JSON-RPC process - it's a
    function from JSON-RPC request string to JSON-RPC response string.

    Args:
        serializer: A function to serialize a Python object to json.
        The rest: Passed through to dispatch_to_serializable.
    """
    response = dispatch_to_serializable(*args, **kwargs)
    # Better to respond with the empty string instead of json "null", because "null" is
    # an invalid JSON-RPC response.
    return "" if response is None else serializer(response)


# "dispatch" aliases dispatch_to_json.
dispatch = dispatch_to_json
