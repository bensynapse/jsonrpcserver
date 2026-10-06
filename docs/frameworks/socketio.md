---
description: A JSON-RPC 2.0 server over Socket.IO with Flask-SocketIO and jsonrpcserver, with a message size limit and max_batch_size set. Tested in CI.
---

# Socket.IO

Using [Flask-SocketIO](https://flask-socketio.readthedocs.io/). Requests
arrive as `message` events, and responses go back the same way.

```python
--8<-- "docs/examples/socketio_server.py"
```

A notification gets nothing back. Flask-SocketIO refuses a message bigger
than `max_http_buffer_size`. Its default is 1,000,000 bytes, and the example
sets it explicitly. `max_batch_size` limits how many requests one batch can
hold. See [Security](../security.md).

The example runs on Werkzeug's development server. Flask-SocketIO's docs
cover the production servers it supports.

## Try it

Install Flask-SocketIO (`pip install flask-socketio`) and run the example.
Any Socket.IO client can call it: connect to `http://localhost:8000`, emit a
`message` event with the request string, and wait for a `message` event with
the response. With [python-socketio](https://python-socketio.readthedocs.io/),
that's `SimpleClient.connect`, `emit("message", request)` and `receive()`.
