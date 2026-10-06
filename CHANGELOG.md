# jsonrpcserver Change Log

## 5.0.10

### Security

When a method raised an exception it didn't catch, the error response sent to
the client included the exception message in `error.data`. Exception messages
from database drivers, HTTP clients and the like often contain connection
strings, passwords, hostnames, file paths or SQL. Anyone who could call a method
could read them.

The response now leaves `data` out:

```json
{"jsonrpc": "2.0", "error": {"code": -32603, "message": "Internal error"}, "id": 1}
```

The same applies to the -32000 "Server error" response for errors inside
jsonrpcserver itself. The exception and its traceback are still logged, through
the `jsonrpcserver.dispatcher` and `jsonrpcserver.async_dispatcher` loggers, so
you can find them in your server logs.

To get the old behaviour back while developing, pass `debug=True` to
`dispatch`, `async_dispatch` or any of the other dispatch functions. Don't turn
it on in production.

Errors you return on purpose, with `Error`, `InvalidParams` or by raising
`JsonRpcError`, are not affected. Their `data` is sent as before.

## 5.0.9 (Sep 15, 2022)

- Remove unncessary `package_data` from setup.py (#243)
- Use a custom logger when logging exceptions, not root

## 5.0.8 (Aug 16, 2022)

- Use importlib.resources instead of pkg_resources.

## 5.0.7 (Mar 10, 2022)

- Upgrade to jsonschema 4.

## 5.0.6 (Jan 14, 2022)

- Fix reversed Result Either type ([#227](https://github.com/explodinglabs/jsonrpcserver/pull/227)).

## 5.0.5 (Nov 27, 2021)

- Documentation.

## 5.0.4 (Oct 27, 2021)

- Add to FAQ.

## 5.0.3

- Update readme and documentation.
- Internal function `compose` has been replaced with a better one.

## 5.0.2

- Update readme and setup.py, minor adjustments.

## 5.0.0 (Aug 16, 2021)

A complete rebuild, with a few important usage changes.

- Methods must now return a Result (Success or Error).
- The dispatch function now returns a string.
- Methods collection is now a simple dict, the Methods class has been removed.
- Changed all classes (Request, Response, Methods, etc) to namedtuples.
- Logging removed. User can log instead.
- Config file removed. Configure with arguments to dispatch.
- Removed "trim log values" and  "convert camel case" options.
- Removed the custom exceptions, replaced with one JsonRpcError exception.

## 4.2.0 (Nov 9, 2020)

- Add ability to use custom serializer and deserializer ([#125](https://github.com/explodinglabs/jsonrpcserver/pull/125))
- Add ability to use custom method name ([#127](https://github.com/explodinglabs/jsonrpcserver/pull/127))
- Deny additional parameters in json-rpc request ([#128](https://github.com/explodinglabs/jsonrpcserver/pull/128))

Thanks to deptyped.

## 4.1.3 (May 2, 2020)

- In the case of a method returning a non-serializable value, return a JSON-RPC
  error response. It was previously erroring server-side without responding to
  the client. (#119)
- Fix for Python 3.8 - ensures the same exceptions will be raised in 3.8 and
  pre-3.8. (#122)

## 4.1.2 (Jan 9, 2020)

- Fix the egg-info directory in package.

## 4.1.1 (Jan 8, 2020)

- Fix file permission on all files.

## 4.1.0 (Jan 6, 2020)

- Add InvalidParamsError exception, for input validation. Previously the
  advice was to `assert` on input values. However, AssertionError was too
  generic an exception. Instead, raise InvalidParamsError. Note `assert` will
  still work but will be removed in the next major release (5.0).
- Add an ApiError exception; raise it to send an application defined error
  response. This covers the line in the JSON-RPC spec, "The remainder of the
  space is available for application defined errors."
- A KeyError raised inside methods will no longer send a "method not found"
  response.
- Uncaught exceptions raised inside methods will now be logged. We've been
  simply responding to the client with a Server Error. Now the traceback will
  also be logged server-side.
- Fix a deprecation warning related to collections.abc.
- Add py.typed to indicate this package supports typing. (PEP 561)

Thanks to steinymity for his work on this release.

## 4.0.5 (Sep 10, 2019)

- Include license in package.

## 4.0.4 (Jun 22, 2019)

- Use faster method of jsonschema validation
- Use inspect from stdlib, removing the need for funcsigs

## 4.0.3 (Jun 15, 2019)

- Update dependencies to allow jsonschema version 3.x
- Support Python 3.8

## 4.0.2 (Apr 13, 2019)

- Fix to allow passing context when no parameters are passed.

## 4.0.1 (Dec 21, 2018)

- Include exception in ExceptionResponse. Closes #74.

## 4.0.0 (Oct 14, 2018)

_The 4.x releases will support Python 3.6+ only._

- Dispatch now works only with `Methods` object. No longer accepts a
  dictionary or list.
- `dispatch` no longer requires a "methods" argument. If not passed, uses the
  global methods object.
- Methods initialiser has a simpler api - Methods(func1, func2, ...) or
  Methods(name1=func1, name2=func2, ...).
- No more jsonrpcserver exceptions. Calling code will _always_ get a valid
  JSON-RPC response from `dispatch`. The old `InvalidParamsError` is gone
  - instead do a regular `assert` on arguments.
- `response.is_notification` renamed to `response.wanted`, which is the
  opposite of is_notification. This means the original request was not a
  notification, it had an id, and does expect a response.
- Removed "respond to notification errors" option, which broke the
  specification. We still respond to invalid json/json-rpc requests, in which
  case it's not possible to know if the request is a notification.
- Removed the "config" module. Added external config file, `.jsonrpcserverrc`.
  (alternatively configure with arguments to dispatch)
- Removed the "six" dependency, no longer needed.
- Configure logging Pythonically.
- Add type hints
- Move tests to pytest
- Passing a context object to dispatch now sets it as the first positional
  argument to the method. `def fruits(ctx, color):`
- Check params with regular asserts.

## 3.5.6 (Jun 28, 2018)
- Add trim_log_values dispatch param. (#65)
- Fix a missing import

## 3.5.5 (Jun 19, 2018)
- Rewrite of dispatch(), adding parameters to configure the dispatch that were
  previously configured by modifying the `config` module. That module is now
  deprecated and will be removed in 4.0.

## 3.5.4 (Apr 30, 2018)
- Refactoring

## 3.5.3 (Dec 19, 2017)
- Allow requests to have any non-None id

## 3.5.2 (Sep 19, 2017)
- Refactor for Request subclassing

## 3.5.1 (Aug 12, 2017)
- Include context data in regular (synchronous) methods.dispatch

## 3.5.0 (Aug 12, 2017)
- Pass some context data through dispatch to the methods.
- Fix not calling notifications in batch requests.

## 3.4.3 (Jul 13, 2017)
- Fix AttributeError on batch responses

## 3.4.3 (Jul 12, 2017)
- Add `Response.is_notification` attribute

## 3.4.2 (Jun 9, 2017)
- Fix `convert_camel_case` with array params

## 3.4.1 (Oct 4, 2016)
- Disable logging in config
- Performance improved
- Fix async batch requests

## 3.4.0 (Sep 27, 2016)
- Added asyncio support. (Python 3.5+)
- Added a *methods* object to the jsonrpcserver module (so you can import
  jsonrpcserver.methods, rather than instantiating your own).
- Added methods.dispatch().

## 3.3.4 (Sep 22, 2016)
- Fix Methods.serve_forever in python 2 (thanks @bplower)

## 3.3.3 (Sep 15, 2016)
- Updated method of logging exception (thanks @bplower)

## 3.3.2 (Aug 19, 2016)
- Pass Methods named args onto MutableMapping
- Remove unused logger

## 3.3.1 (Aug 5, 2016)
- Allow passing dict to Methods constructor

## 3.3.0 (Aug 5, 2016)
- A basic HTTP server has been added.
