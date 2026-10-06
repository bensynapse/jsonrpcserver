---
description: Use jsonrpcserver with any Python framework or transport. Complete, tested examples for http.server, Flask, Werkzeug, Django, FastAPI, aiohttp, Sanic, Tornado, websockets, ZeroMQ and Socket.IO.
---

# Frameworks

jsonrpcserver doesn't do the networking. You receive the request with a
framework or transport library, pass it to `dispatch` or `async_dispatch`,
and send back the result. Each page below has a complete example that answers
`ping` with `pong` on `localhost:8000`. CI starts every one of them and sends
it real requests, including a batch that's too big and, for HTTP, a body
that's too big.

| Framework | Transport | Sync or async | Body size limit in the example | Page |
|---|---|---|---|---|
| `http.server` (standard library) | HTTP | sync | checked by hand | [http.server and serve()](frameworks/http-server.md) |
| [Flask](https://flask.palletsprojects.com/) | HTTP | sync | `MAX_CONTENT_LENGTH` | [Flask](frameworks/flask.md) |
| [Werkzeug](https://werkzeug.palletsprojects.com/) | HTTP | sync | `max_content_length` | [Werkzeug](frameworks/werkzeug.md) |
| [Django](https://www.djangoproject.com/) | HTTP | sync | `DATA_UPLOAD_MAX_MEMORY_SIZE` | [Django](frameworks/django.md) |
| [FastAPI](https://fastapi.tiangolo.com/) | HTTP | async | checked by hand | [FastAPI](frameworks/fastapi.md) |
| [aiohttp](https://docs.aiohttp.org/) | HTTP | async | `client_max_size` | [aiohttp](frameworks/aiohttp.md) |
| [Sanic](https://sanic.dev/) | HTTP | async | `REQUEST_MAX_SIZE` | [Sanic](frameworks/sanic.md) |
| [Tornado](https://www.tornadoweb.org/) | HTTP | async | `max_body_size` | [Tornado](frameworks/tornado.md) |
| [websockets](https://websockets.readthedocs.io/) | WebSocket | async | `max_size` | [websockets](frameworks/websockets.md) |
| [pyzmq](https://pyzmq.readthedocs.io/) | ZeroMQ | both | `MAXMSGSIZE` | [ZeroMQ](frameworks/zeromq.md) |
| [Flask-SocketIO](https://flask-socketio.readthedocs.io/) | Socket.IO | sync | `max_http_buffer_size` | [Socket.IO](frameworks/socketio.md) |

The pattern is the same everywhere:

1. Read the request body as a string. Refuse one that's too big before you
   read it.
2. Pass it to `dispatch`, or `await async_dispatch(...)` in an async
   framework, with `max_batch_size` set.
3. If the result is a non-empty string, send it with
   `Content-Type: application/json` and status 200. If it's empty, the
   request was a notification: over HTTP, send status 204 with no body. Over
   other transports, send nothing (ZeroMQ's REQ/REP sockets are the exception:
   they must reply, so send the empty string).

A JSON-RPC error is still a successful HTTP exchange, so it's sent with
status 200 too.

Every example limits the body to 1,000,000 bytes and batches to 100 requests.
Pick limits that fit your methods. [Security](security.md) explains why both
matter. To give methods the request or the logged-in user, see
[Context](context.md).

!!! tip "Port 8000"
    The examples use port 8000, the same as the
    [jsonrpcclient](https://bensynapse.github.io/jsonrpcclient/) examples.
    Run one of each and they talk to each other. Port 5000, which many
    tutorials use, is taken by the AirPlay Receiver on recent macOS versions.

The examples listen on `localhost` only. To accept connections from other
machines, change it to the address you want. Then put the server behind a
production web server, as each framework's docs describe.
