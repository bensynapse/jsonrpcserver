<p align="center">
  <a href="https://pypi.org/project/jsonrpcserver/"><img src="https://img.shields.io/pypi/v/jsonrpcserver.svg" alt="PyPI version" /></a>
  <a href="https://github.com/bensynapse/jsonrpcserver/actions/workflows/ci.yml"><img src="https://github.com/bensynapse/jsonrpcserver/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://bensynapse.github.io/jsonrpcserver/#install"><img src="https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue" alt="Python 3.8 to 3.14" /></a>
  <a href="https://pypistats.org/packages/jsonrpcserver"><img src="https://img.shields.io/pypi/dm/jsonrpcserver" alt="Downloads per month" /></a>
  <a href="https://github.com/bensynapse/jsonrpcserver/blob/main/LICENSE"><img src="https://img.shields.io/github/license/bensynapse/jsonrpcserver" alt="License: MIT" /></a>
</p>

<p align="center">
  <img alt="jsonrpcserver" src="https://raw.githubusercontent.com/bensynapse/jsonrpcserver/main/logo.png" />
</p>

<p align="center">
  <i>Process incoming JSON-RPC 2.0 requests in Python</i>
</p>

<p align="center">
  <a href="https://bensynapse.github.io/jsonrpcserver/">Documentation</a> |
  <a href="https://bensynapse.github.io/jsonrpcserver/reference/">API reference</a> |
  <a href="https://bensynapse.github.io/jsonrpcserver/examples/">Examples</a> |
  <a href="https://bensynapse.github.io/jsonrpcserver/changelog/">Changelog</a> |
  <a href="https://bensynapse.github.io/jsonrpcserver/migration/">Migration</a>
</p>

jsonrpcserver takes a [JSON-RPC 2.0](https://www.jsonrpc.org/specification)
request, calls your Python function and gives you the response to send back.
It leaves the networking to you, so it fits into whatever server you already
have.

## Features

- Works with any framework or transport. The docs have tested examples for
  http.server, Flask, Werkzeug, Django, FastAPI, aiohttp, Sanic, Tornado,
  websockets, ZeroMQ and Socket.IO.
- Sync and async: `dispatch` and `async_dispatch`. With `async_dispatch`, the
  requests in a batch run concurrently.
- Follows the spec for batches, notifications and errors, and checks each
  request's params against your function's signature.
- Keeps exception messages out of responses and in your logs, and limits
  batch size with `max_batch_size` (from 5.0.10).
- Typed: ships `py.typed`, and `@method` keeps your functions' signatures for
  mypy and pyright.
- Safe to call from several threads, and tested on Python 3.8 to 3.14,
  including free-threaded 3.14t.

## Install

```sh
pip install jsonrpcserver
```

The latest release on PyPI is 5.0.9. This README and the documentation
describe 5.0.10, which isn't released yet. 5.0.9 sends exception messages to
clients. The
[Security page](https://bensynapse.github.io/jsonrpcserver/security/#if-you-are-on-509)
shows how to stop that, and the
[changelog](https://bensynapse.github.io/jsonrpcserver/changelog/) lists the
other differences.

## Quickstart

Save this as `server.py` and run it with `python server.py`:

<!-- skip: it runs forever. docs/examples/check_examples.py runs the same file. -->
```python
from jsonrpcserver import Result, Success, method, serve


@method
def ping() -> Result:
    return Success("pong")


if __name__ == "__main__":
    serve("localhost", 8000)
```

Then send it a request from another terminal:

```sh
curl -s -H 'Content-Type: application/json' -d '{"jsonrpc": "2.0", "method": "ping", "id": 1}' http://localhost:8000/
```

Output:

```text
{"jsonrpc": "2.0", "result": "pong", "id": 1}
```

`serve()` is a small server for trying things out. In your own framework,
pass the request body to `dispatch` and send back the string it returns. The
[examples](https://bensynapse.github.io/jsonrpcserver/examples/) show how.

## Security

Before you put a server on the internet, pass `max_batch_size` to `dispatch`
and limit the request body size in your framework. Upgrade to 5.0.10 when
it's out. The
[Security page](https://bensynapse.github.io/jsonrpcserver/security/)
explains why.

## Documentation

- [Documentation](https://bensynapse.github.io/jsonrpcserver/): guides,
  framework examples and the
  [API reference](https://bensynapse.github.io/jsonrpcserver/reference/).
- [Migrating from 4.x](https://bensynapse.github.io/jsonrpcserver/migration/):
  methods must now return `Success(value)`. A 4.x method that returns a plain
  value still runs, but the client gets an Internal error.
- [Contributing](https://github.com/bensynapse/jsonrpcserver/blob/main/CONTRIBUTING.md)
  and the
  [security policy](https://github.com/bensynapse/jsonrpcserver/blob/main/SECURITY.md).
- [License](https://github.com/bensynapse/jsonrpcserver/blob/main/LICENSE): MIT.

## See also

[jsonrpcclient](https://bensynapse.github.io/jsonrpcclient/)
([GitHub](https://github.com/bensynapse/jsonrpcclient)) creates JSON-RPC
requests and parses the responses in Python. It's the client-side companion
to this library, and its quickstart talks to the server above.

## Credits

Created by Beau Barker. Maintained by [Synapse Research](https://synapsereality.io).
