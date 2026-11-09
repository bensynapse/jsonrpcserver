---
title: JSON-RPC 2.0, section by section
description: The rules of the JSON-RPC 2.0 spec, with what jsonrpcserver does and its test. Request and response objects, notifications, batches, error codes and where the library differs.
---

# JSON-RPC 2.0, section by section

This page takes the rules of the
[JSON-RPC 2.0 specification](https://www.jsonrpc.org/specification)
(last updated 2013-01-04) in order. For each one it says what jsonrpcserver
does and links the test that shows it. The tests run on every pull request.
Where jsonrpcserver does something else, the
[last section](#where-jsonrpcserver-differs) says so.

This is the page for 5.x. The 6.0 copy differs where 6.0 behaves differently.

Everything here is about the default `dispatch`, `async_dispatch` and
`dispatch_to_response`, with the default deserializer and validator. A
[custom validator](validation.md) or deserializer changes what counts as a
valid request.

## 4. The request object

| The spec says | jsonrpcserver | Test |
|---|---|---|
| `jsonrpc` MUST be exactly `"2.0"`. | Anything else, or no `jsonrpc` member, gets -32600 Invalid request. | [`test_jsonrpc_must_be_exactly_2_0`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py), [`test_jsonrpc_member_is_required`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |
| `method` is a String. | A number, null or anything else gets -32600. | [`test_method_must_be_a_string`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |
| Names starting with `rpc.` are reserved and MUST NOT be used for anything else. | `@method` warns with a UserWarning and registers the method anyway. A methods dict you pass yourself isn't checked. Either way, a request can call an `rpc.` method. | [`test_rpc_names_registered_with_method_are_called`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py), [`test_rpc_names_in_a_methods_dict_are_called`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |
| `params` MAY be omitted. | The method is called with no arguments. | [`test_dispatch_to_response_pure`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py) |
| `id`, if included, MUST be a String, Number or Null. | A boolean, array or object gets -32600. | [`test_id_that_is_not_a_string_number_or_null`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |
| `id` SHOULD normally not be Null, and Numbers SHOULD NOT have fractional parts. | Both are accepted. These rules are for the client. | [`test_id_is_returned_unchanged`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |
| The server MUST reply with the same `id` value. | The id goes back as it came: string, integer, fraction or null. | [`test_id_is_returned_unchanged`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |

The spec doesn't say what to do with members other than these four.
jsonrpcserver rejects a request that has any, with -32600
([`test_unknown_members_are_an_invalid_request`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py)).
Member names are case-sensitive (section 2), so `"JSONRPC"` is one of those
other members
([`test_member_names_are_case_sensitive`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py)).

### 4.1 Notifications

| The spec says | jsonrpcserver | Test |
|---|---|---|
| A request without an `id` member is a notification. The server MUST NOT reply to it. | The method runs. `dispatch` gives an empty string, `dispatch_to_response` gives None and `serve()` sends HTTP 204. | [`test_examples_notification`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py), [`test_dispatch_to_json_notification`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_main.py), [`test_notification`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_server.py) |
| The client doesn't hear about errors such as Invalid params or Internal error. | No response for an unknown method, params that don't fit, or a method that raises. | [`test_dispatch_to_response_pure_notification_method_not_found`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py), [`test_dispatch_to_response_pure_notification_invalid_params_auto`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py), [`test_dispatch_to_response_pure_notification_internal_error`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py) |
| No reply to notifications inside a batch either. | Notifications in a batch get no response, failed or not. | [`test_failing_notifications_in_a_batch_get_no_response`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |
| A request with `"id": null` is not a notification. | It gets a response with `"id": null`. | [`test_batch_keeps_valid_members`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_async_dispatcher.py) |

A request that isn't valid can't be told apart from a notification, so it
gets a -32600 response even with no `id`
([`test_dispatch_to_response_pure_notification_invalid_request`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py)).

### 4.2 Parameters

| The spec says | jsonrpcserver | Test |
|---|---|---|
| `params`, if present, MUST be an Array or an Object. | A string, number, boolean or null gets -32600. | [`test_params_must_be_structured`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |
| By position: an Array, in the order the server expects. | Passed as positional arguments. | [`test_examples_positionals`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py) |
| By name: an Object whose names match the parameter names. | Passed as keyword arguments. | [`test_examples_nameds`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py) |
| Missing names MAY cause an error. | Params that don't fit the function's signature get -32602, with the reason in `data`. | [`test_dispatch_to_response_pure_invalid_params_auto`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py) |
| Names MUST match exactly, including case. | `{"Colour": ...}` doesn't fill a `colour` parameter, so it gets -32602. | [`test_params_by_name_match_case`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |

## 5. The response object

| The spec says | jsonrpcserver | Test |
|---|---|---|
| The server MUST reply to every call, except notifications. | Every request with an `id` gets a response. See 4.1 for notifications. | [`test_examples_mixed_requests_and_notifications`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py) |
| `jsonrpc` MUST be exactly `"2.0"`. | It is in every response. | [`test_to_serializable_SuccessResponse`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_response.py) |
| `result` is REQUIRED on success and MUST NOT exist on error. `error` is the other way round, and MUST be an Object. Never both. | A success has `result` and no `error`. An error has `error` and no `result`. | [`test_to_serializable_SuccessResponse`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_response.py), [`test_to_serializable_ErrorResponse`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_response.py) |
| `id` is REQUIRED and MUST be the request's `id`. | See 4. | [`test_id_is_returned_unchanged`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |
| If the id couldn't be read (Parse error, Invalid Request), `id` MUST be Null. | -32700 and -32600 responses always have `"id": null`, even when the invalid request had an id. | [`test_dispatch_to_response_pure_parse_error`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py), [`test_id_that_is_not_a_string_number_or_null`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |

### 5.1 The error object

| The spec says | jsonrpcserver | Test |
|---|---|---|
| `code` MUST be an integer. | `Error()` and `JsonRpcError` warn with a UserWarning for anything else, booleans included. The error is still sent as it was made. | [`test_error_warns`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_warnings.py), [`test_jsonrpcerror_warns`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_warnings.py), [`test_a_bad_error_is_sent_as_given`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py), [`test_a_bad_jsonrpcerror_is_sent_as_given`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |
| `message` is a String, and SHOULD be one short sentence. | The same: a warning, and the error is sent as it was made. | [`test_jsonrpcerror_warns`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_warnings.py), [`test_a_bad_error_is_sent_as_given`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |
| `data` may be omitted. | With no data, the response has no `data` member. | [`test_dispatch_to_response_pure_invalid_params_explicitly_returned`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py), [`test_server_error_range_is_passed_through`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |
| -32768 to -32000 are reserved for the spec's own errors. Codes in that range that the spec doesn't define are reserved for future use. | `Error()` accepts any integer, reserved or not, and sends it unchanged. Its docstring asks you to pick numbers outside the range. | [`test_methods_can_use_reserved_codes`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |

[Errors and logging](errors.md) says what each code's `data` holds and what
gets logged.

### The error codes

| Code | The spec says | jsonrpcserver sends it when | Test |
|---|---|---|---|
| -32700 | Parse error: invalid JSON was received. | The body isn't JSON. RFC 8259 doesn't allow `NaN` or `Infinity`, but 5.x reads them. See the last section. | [`test_dispatch_to_response_pure_parse_error`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py) |
| -32600 | Invalid Request: the JSON isn't a valid request object. | The request breaks a rule in section 4, a batch is empty, or a batch is over `max_batch_size` if you set one. | [`test_dispatch_to_response_pure_invalid_request`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py), [`test_over_the_limit`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_batch_limit.py) |
| -32601 | Method not found. | No method has that name. `data` is the name. | [`test_dispatch_to_response_pure_method_not_found`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py) |
| -32602 | Invalid params. | The params don't fit the signature, or the method returns `InvalidParams()`. | [`test_dispatch_to_response_pure_invalid_params_auto`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py), [`test_dispatch_to_response_pure_invalid_params_explicitly_returned`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py) |
| -32603 | Internal error. | The method raises, or its result can't be serialized. The exception message is only in `data` with `debug=True`. | [`test_dispatch_to_response_pure_internal_error`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py), [`test_unserializable_result`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_robustness.py) |
| -32000 to -32099 | Server error: reserved for the implementation. | jsonrpcserver itself fails, outside any method: -32000 Server error. A single request gets `"id": null`. In a batch, the member keeps its own id, and a notification gets null. A method can also return any code in this range, and it's sent unchanged. | [`test_dispatch_to_response_pure_server_error`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py), [`test_server_error_in_a_batch_keeps_member_ids`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py), [`test_server_error_range_is_passed_through`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |

## 6. Batches

| The spec says | jsonrpcserver | Test |
|---|---|---|
| A batch is an Array of requests. The server should respond with an Array of the responses, once all of them have been processed. | Each member is run, and the responses come back as an array. | [`test_examples_mixed_requests_and_notifications`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py) |
| A response SHOULD exist for each request, and SHOULD NOT exist for notifications. | Same. | [`test_examples_mixed_requests_and_notifications`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py) |
| The server MAY process the requests concurrently, in any order. | `dispatch` runs them one after another. `async_dispatch` runs them concurrently. | [`test_batch_async_members_run_concurrently`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_async_dispatcher.py) |
| Responses MAY come back in any order. | They come back in request order. Match them by `id` anyway. | [`test_examples_mixed_requests_and_notifications`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py) |
| If the batch isn't valid JSON, the response MUST be a single response object. | One -32700 response, not an array. | [`test_examples_invalid_json`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py) |
| An empty Array MUST get a single response object. | One -32600 response, not an array. | [`test_examples_empty_array`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py), [`test_batch_response_shape`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_async_dispatcher.py) |
| JSON that is neither an object nor an Array MUST get a single response object. | One -32600 response. | [`test_json_that_is_not_an_object_or_array`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |
| Invalid members, as in `[1]` or `[1, 2, 3]`, each get their own error in the Array. | Each invalid member gets its own -32600, and the valid members still run. | [`test_examples_invalid_jsonrpc_batch`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py), [`test_examples_multiple_invalid_jsonrpc`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py), [`test_batch_keeps_valid_members`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_async_dispatcher.py) |
| If there are no responses to send, the server MUST NOT return an empty Array, and should return nothing. | A batch of only notifications gives an empty string, or None from `dispatch_to_response`. | [`test_extract_list_batch_all_notifications`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py), [`test_batch_response_shape`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_async_dispatcher.py), [`test_failing_notifications_in_a_batch_get_no_response`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py) |

[Notifications and batches](batches.md) has examples of each case.

## Where jsonrpcserver differs

These are the places where jsonrpcserver doesn't do what the spec says, or
goes further than it.

### A batch over `max_batch_size` gets one -32600 response

The spec has no batch limit, and 5.x has none by default. If you pass
`max_batch_size`, a batch over the limit runs nothing. It gets the error
even if every member is a notification
([`test_over_the_limit_notifications`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_batch_limit.py)).
The [Security page](security.md) explains why you should set it. 6.0 sets
it to 100 by default.

### A notification can get a -32000 response

If jsonrpcserver itself fails while it handles a notification, it sends
-32000 Server error with `"id": null`, on its own or inside a batch. The
spec says never to reply to a notification. It happens only when something
fails outside your methods, such as a bug in jsonrpcserver. A notification
whose method fails still gets no response
([`test_dispatch_to_response_pure_notification_server_error`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py),
[`test_server_error_in_a_batch_keeps_member_ids`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py)).

### Unknown members are rejected

A request with a member other than `jsonrpc`, `method`, `params` and `id`
gets -32600. The spec doesn't forbid them
([`test_unknown_members_are_an_invalid_request`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py)).

### `rpc.` names can be used

`@method` warns about an `rpc.` name but registers the method. A methods
dict isn't checked at all. A request can call the method either way
([`test_rpc_prefix_warns`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_warnings.py),
[`test_rpc_names_in_a_methods_dict_are_called`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py)).
6.0 makes `@method` raise ValueError.

### Error codes that aren't integers are sent

`Error(1.5, "msg")` and `JsonRpcError(True, "msg")` give a UserWarning, and
the response carries the code as given. The same goes for a message that
isn't a string
([`test_a_bad_error_is_sent_as_given`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py)). 6.0
raises TypeError when the error is made.

### NaN and Infinity in a request are read

`NaN`, `Infinity` and `-Infinity` aren't JSON, so they should get -32700
Parse error. 5.x reads them as Python floats and gives a FutureWarning
([`test_non_json_constants_are_accepted`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py)). A number too big for a float,
such as `1e400`, is read as infinity. As an id, it gets -32603 with
`"id": null`, after the method has already run
([`test_infinite_id_runs_the_method_first`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py)). 6.0 sends -32700
for all of them, before any method runs.

### Methods can send reserved codes

Nothing stops a method from returning `Error(-32601, ...)` or any other code
the spec reserves. It's sent unchanged
([`test_methods_can_use_reserved_codes`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py)).

### The -32600 message is "Invalid request"

The spec's table spells it "Invalid Request". The spec doesn't require the
exact text, but a client that compares messages will see the difference
([`test_examples_mixed_requests_and_notifications`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_dispatcher.py)).

### JSON-RPC 1.0 requests aren't handled

Section 3 suggests 2.0 servers try to handle 1.0 requests. jsonrpcserver
answers them with -32600
([`test_jsonrpc_member_is_required`](https://github.com/bensynapse/jsonrpcserver/blob/release/5.x/tests/test_spec.py)).

Each row links the tests that show it. If you find a case that doesn't match
the spec, please [open an
issue](https://github.com/bensynapse/jsonrpcserver/issues).
