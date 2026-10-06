"""The error codes jsonrpcserver sends.

The first five are defined by the spec:
https://www.jsonrpc.org/specification#error_object
"""

ERROR_PARSE_ERROR = -32700
"""The request isn't valid JSON (or the deserializer raised)."""
ERROR_INVALID_REQUEST = -32600
"""The JSON isn't a valid request object, or a batch is empty or too big."""
ERROR_METHOD_NOT_FOUND = -32601
"""No method has that name."""
ERROR_INVALID_PARAMS = -32602
"""The params don't fit the method's signature, or the method said they're invalid."""
ERROR_INTERNAL_ERROR = -32603
"""The method raised, returned something other than a Result, or its result
could not be serialized.
"""
ERROR_SERVER_ERROR = -32000
"""Something failed in jsonrpcserver itself, outside any method."""
