---
description: The plan for jsonrpcserver 6.0. Results without oslash, safer defaults, a faster validator, and cleanups. 5.x keeps its API and gets fixes.
---

# Roadmap

This is the plan for the next major version. Nothing here is released yet, and
it may change. 5.x keeps its current API, and gets bug and security fixes.

Discussion happens in the
[issues](https://github.com/bensynapse/jsonrpcserver/issues) and
[discussions](https://github.com/bensynapse/jsonrpcserver/discussions). An
older draft of 6.0 exists as a pull request from 2022. It's out of date, and
the plan below replaces it.

## 6.0

These change behaviour or remove things, so they wait for a major version.

**Results without oslash.** `Success`, `Error` and the dispatch functions are
built on the oslash library. Its last release for Python 3.8 to 3.11 came out
in 2020, and its newer releases need Python 3.12. 6.0 will replace it with
small typed result classes of its own, or with another maintained library.
Code that only uses `Success`, `Error` and `dispatch` should keep working.
Code that inspects the `Left` and `Right` objects from `dispatch_to_response`
will need changes.

**Safer defaults.**

- A default `max_batch_size`, instead of no limit.
- Reject `NaN`, `Infinity` and out-of-range numbers in requests by default.
- Make an `Error` with a non-integer code an error, not a warning. The same
  goes for method names starting with `rpc.`.
- Optionally, a limit on how many requests of a batch `async_dispatch` runs
  at once.

**A faster validator.** Schema validation with jsonschema takes about three
quarters of the dispatch time for small methods. jsonschema also pulls in a
Rust extension through its dependencies. A small hand-written check of the
five request fields would be faster and lighter.

**Cleanups.**

- Remove `serialize_error`, `serialize_success` and `to_serializable_one`,
  which 5.0.10 deprecated.
- Decide whether async methods need their own decorator, or whether
  `async_dispatch` keeps accepting both kinds. Use the same option names and
  return types in the sync and async functions.
- Rework or remove the built-in `serve()` development server.
- Drop Python versions that have reached end of life.

**Ideas under discussion.**

- Let a method return a plain value instead of `Success(value)` (#285).
- Middleware around method calls (#126). Decorators on your own functions
  already cover most uses.
- OpenRPC schema generation (#156), probably as a separate package.
