<style>
.md-content__inner h1:first-of-type {
  display: none;
}
</style>

# jsonrpcserver

![jsonrpcserver](assets/logo.png)

_Process incoming JSON-RPC requests in Python._

jsonrpcserver takes a [JSON-RPC 2.0](https://www.jsonrpc.org/specification)
request string, calls your function and gives you the response string. It
doesn't listen on a port itself, so it works with any framework or transport:
HTTP, websockets, ZeroMQ, message queues and so on.

## Installation

```sh
pip install jsonrpcserver
```

It supports Python 3.8 and later.

## Quick start

Write a method:

```python
from jsonrpcserver import Result, Success, dispatch, method


@method
def ping() -> Result:
    return Success("pong")
```

Then pass the request to `dispatch`:

```python
>>> dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}')
'{"jsonrpc": "2.0", "result": "pong", "id": 1}'
```

Send that string back to the client. For a notification (a request without an
`id`), `dispatch` gives an empty string, meaning there's nothing to send:

```python
>>> dispatch('{"jsonrpc": "2.0", "method": "ping"}')
''
```

## Next

- [Methods](methods.md): writing methods, parameters and errors.
- [Dispatch](dispatch.md): the options `dispatch` takes.
- [Async](async.md): `async_dispatch` for asyncio servers.
- [Examples](examples.md): Flask, FastAPI, Django, aiohttp, websockets,
  ZeroMQ and more.
- [Security](security.md): what to set before you expose a server.
- [FAQ](faq.md)

jsonrpcclient, the companion library for the other end of the connection, is
at [bensynapse/jsonrpcclient](https://github.com/bensynapse/jsonrpcclient).
