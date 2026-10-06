---
title: Process incoming JSON-RPC 2.0 requests in Python
description: jsonrpcserver turns JSON-RPC 2.0 requests into calls to your Python functions. It works with any framework or transport, sync or async, and is typed and thread-safe.
---

# jsonrpcserver

_Process incoming JSON-RPC 2.0 requests in Python._

jsonrpcserver takes a [JSON-RPC 2.0](https://www.jsonrpc.org/specification)
request, calls your Python function and gives you the response to send back.
It leaves the networking to you, so it works with any framework or transport:
Flask, Django, FastAPI, aiohttp, websockets, ZeroMQ and more. It runs sync and
async methods, ships type hints, and is safe to use from several threads. It
supports Python 3.8 to 3.14, including free-threaded 3.14t.

## Install

```sh
pip install jsonrpcserver
```

## Quickstart

Save this as `server.py`:

```python
--8<-- "docs/examples/quickstart.py"
```

Run it with `python server.py` and leave it running. `serve()` is a small
server for trying things out. In production you'd use your web framework
instead, as in the [framework examples](examples.md).

In another terminal, send it a request with curl:

```sh
curl -s -H 'Content-Type: application/json' -d '{"jsonrpc": "2.0", "method": "ping", "id": 1}' http://localhost:8000/
```

```text title="Output"
{"jsonrpc": "2.0", "result": "pong", "id": 1}
```

Or call it from Python with
[jsonrpcclient](https://bensynapse.github.io/jsonrpcclient/), the companion
library for the client side (`pip install jsonrpcclient requests`):

<!-- requires: jsonrpcclient -->
<!-- server -->
```python
import requests
from jsonrpcclient import Error, Ok, parse, request

url = "http://localhost:8000/"
response = requests.post(url, json=request("ping"), timeout=10)
response.raise_for_status()
parsed = parse(response.json())
if isinstance(parsed, Ok):
    print(parsed.result)
elif isinstance(parsed, Error):
    print("Error:", parsed.message)
```

```text title="Output"
pong
```

### What happens inside

The server passes each request body to `dispatch`, which calls your method and
gives back the response as a string:

```pycon
>>> from jsonrpcserver import Result, Success, dispatch, method
>>> @method
... def ping() -> Result:
...     return Success("pong")
>>> dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}')
'{"jsonrpc": "2.0", "result": "pong", "id": 1}'
```

That's all there is to it in your own framework: pass the request body to
`dispatch` and send back what it gives you. A notification (a request with no
`id`) gives an empty string, which means there's nothing to send:

```pycon
>>> dispatch('{"jsonrpc": "2.0", "method": "ping"}')
''
```

Over HTTP, answer that with status 204 and no body.

## Where next

- [Methods](methods.md) and [Dispatch](dispatch.md): writing methods, and the
  options `dispatch` takes.
- [Frameworks](examples.md): complete, tested examples for http.server,
  Flask, Werkzeug, Django, FastAPI, aiohttp, Sanic, Tornado, websockets, ZeroMQ
  and Socket.IO.
- [Security](security.md): what to set before you put a server on the
  internet.
- [Errors and logging](errors.md): every error the client can get, and where
  the details go.
- [API reference](reference.md): every function and class, with signatures.
- [Migrating from 4.x](migration.md): methods must now return `Success(...)`.
- [jsonrpcclient](https://bensynapse.github.io/jsonrpcclient/): the same idea
  for the client side.
