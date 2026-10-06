---
description: API reference for jsonrpcserver, generated from the source code. Every public function and class, with signatures, parameters, return values and exceptions.
---

# API reference

This page is generated from the docstrings in the source code, so it matches
the code on the main branch.

Everything in the first five sections can be imported from the package
itself, for example `from jsonrpcserver import Success, dispatch, method`.
The two `dispatch_to_json` entries are the exception: they're the functions
behind `dispatch` and `async_dispatch`, and live in `jsonrpcserver.main` and
`jsonrpcserver.async_main`. The other public names are in `jsonrpcserver.response`,
`jsonrpcserver.result`, `jsonrpcserver.codes`, `jsonrpcserver.methods` and
`jsonrpcserver.sentinels`. Anything not listed here is internal and can change
in any release.

In the signatures, `context=NOCONTEXT` means "no context": methods get only
the request's params. `data=NODATA` means the error has no `data` member.

## Methods and results

::: jsonrpcserver.method

::: jsonrpcserver.Success

::: jsonrpcserver.Error

::: jsonrpcserver.InvalidParams

::: jsonrpcserver.JsonRpcError

::: jsonrpcserver.Result

## Dispatch

::: jsonrpcserver.dispatch

::: jsonrpcserver.main.dispatch_to_json
    options:
      show_root_full_path: true

::: jsonrpcserver.dispatch_to_serializable

::: jsonrpcserver.dispatch_to_response

## Async dispatch

::: jsonrpcserver.async_dispatch

::: jsonrpcserver.async_main.dispatch_to_json
    options:
      show_root_full_path: true

::: jsonrpcserver.async_dispatch_to_serializable

::: jsonrpcserver.async_dispatch_to_response

## Development server

::: jsonrpcserver.serve

## Version

::: jsonrpcserver.__version__

## Responses

::: jsonrpcserver.response.Response

::: jsonrpcserver.response.SuccessResponse

::: jsonrpcserver.response.ErrorResponse

::: jsonrpcserver.response.to_dict

::: jsonrpcserver.response.to_success_dict

::: jsonrpcserver.response.to_error_dict

::: jsonrpcserver.response.to_serializable

## Results

::: jsonrpcserver.result.SuccessResult

::: jsonrpcserver.result.ErrorResult

## Error codes

::: jsonrpcserver.codes
    options:
      show_root_heading: false
      show_root_toc_entry: false

## Other names

::: jsonrpcserver.methods.global_methods

::: jsonrpcserver.sentinels.NODATA

::: jsonrpcserver.sentinels.NOCONTEXT

## Deprecated

These still work in 5.x, but give a `DeprecationWarning` and will be removed
in 6.0.

::: jsonrpcserver.response.serialize_error

::: jsonrpcserver.response.serialize_success

::: jsonrpcserver.response.to_serializable_one

::: jsonrpcserver.response.ResponseType
