---
description: A JSON-RPC 2.0 server with Python's built-in http.server and jsonrpcserver, with no other dependencies. Plus serve(), the development server that comes with jsonrpcserver.
---

# http.server and serve()

## http.server

Python's built-in HTTP server, with no other dependencies. It reads the body
itself, so it also has to check the `Content-Length` header, refuse a body
that's too big and handle bytes that aren't UTF-8:

```python
--8<-- "docs/examples/http_server.py"
```

A missing `Content-Length` gets 411, a body over the limit gets 413, and a
body that isn't UTF-8 gets a -32700 "Parse error". http.server is fine for
small internal tools. For anything public, use a framework or put a
production web server in front.

## serve()

jsonrpcserver also has a small built-in server, `serve()`. It's for trying
things out, not for production:

```python
--8<-- "docs/examples/quickstart.py"
```

It answers POST requests on any path, sends 204 for notifications, and
handles each request in its own thread. It also handles a missing
`Content-Length` (411) and a body that isn't UTF-8 (-32700).

Know its limits before you use it:

- It listens on every network interface unless you pass a host, as the
  example does with `"localhost"`. With `serve()` and no arguments, anyone
  who can reach your machine on port 5000 can call your methods.
- It has no TLS, no authentication and no limit on the body size, and it
  doesn't set `max_batch_size`.
- It says where it's listening when it starts (new in 5.0.10). Each request
  is logged on the `jsonrpcserver.server` logger at INFO level, so
  `logging.basicConfig(level=logging.INFO)` shows them.

!!! info "Changed in 5.0.10"
    In 5.0.9, `serve()` answers a notification with 200 and an empty body
    instead of 204, and prints nothing when it starts. It drops the
    connection for a missing `Content-Length` or a body that isn't UTF-8.

## Try it

Save the serve() example as `quickstart.py` and run it:

```sh
python quickstart.py
```

Then send it a request from another terminal:

```sh
curl -s -H 'Content-Type: application/json' -d '{"jsonrpc": "2.0", "method": "ping", "id": 1}' http://localhost:8000/
```

```text title="Output"
{"jsonrpc": "2.0", "result": "pong", "id": 1}
```

The [jsonrpcclient quickstart](https://bensynapse.github.io/jsonrpcclient/#quickstart)
sends the same request from Python.
