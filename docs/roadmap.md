---
description: The plan for jsonrpcserver 6.0, in development on main. No dependencies, safer defaults, a faster validator, and cleanups. 5.x keeps its API and gets fixes.
---

# Roadmap

6.0 is in development on the main branch. It isn't released yet, and it may
still change. [#320](https://github.com/bensynapse/jsonrpcserver/issues/320)
tracks it, and [Migration](migration.md#from-5x-to-60) lists every change.
5.x keeps its current API, and gets bug and security fixes on the
`release/5.x` branch.

## 6.0

These change behaviour or remove things, so they wait for a major version.

**Done on main:**

- **No dependencies.** `Success`, `Error` and the dispatch functions return
  small dataclasses of their own instead of oslash's `Right` and `Left`. A
  hand-written check of the request fields replaces jsonschema, and makes
  dispatching a small method about four times faster.
- **Python 3.11 or later.** 3.8, 3.9 and 3.10 have reached end of life.
- **Safer defaults.**
    - Batches hold at most 100 requests unless you set `max_batch_size`.
    - `NaN`, `Infinity` and numbers too big for a float in a request are a
      Parse error.
    - An `Error` with a non-integer code is a `TypeError`, and a method name
      starting with `rpc.` is a `ValueError`. 5.0.10 warned.
    - `serve()` listens on localhost unless you give it a host.
- **`max_concurrency`** limits how many requests of a batch `async_dispatch`
  runs at once.
- **Cleanups.** The names 5.0.10 deprecated are gone. The sync and async
  dispatch functions take the same options. One `@method` decorator serves
  sync and async functions.

**Next:**

- 5.2.0, from `release/5.x`, warns where code depends on something 6.0
  changes.
- A release candidate, 6.0.0rc1, then 6.0.0.

## Ideas under discussion

- Middleware around method calls (#126). Decorators on your own functions
  already cover most uses.
- OpenRPC schema generation (#156), probably as a separate package.

5.1.0 took one idea from this list early: a method can return a plain value
(#285).
