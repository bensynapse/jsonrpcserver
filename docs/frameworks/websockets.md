---
description: A JSON-RPC 2.0 server over WebSocket with the websockets library and jsonrpcserver's async_dispatch, with a message size limit and max_batch_size set. Tested in CI.
---

# websockets

Uses the `websockets.asyncio` server from
[websockets](https://websockets.readthedocs.io/) 13 and later.

```python
--8<-- "docs/examples/websockets_server.py"
```

Unlike HTTP, a WebSocket doesn't need an answer to every message, so a
notification gets nothing back. websockets closes the connection if a message
is bigger than `max_size`. Its default is 1 MiB (1,048,576 bytes). The
example sets 1,000,000, like the other examples. `max_batch_size` limits how many requests one batch can hold. See
[Security](../security.md).

Requests on one connection are handled one at a time, in the order they
arrive. To answer them concurrently, start a task for each message.

## Try it

Save the example as `websockets_server.py`, install websockets
(`pip install websockets`), and run it:

```sh
python websockets_server.py
```

websockets comes with an interactive client. Run
`python -m websockets ws://localhost:8000/` in another terminal and type a
request, such as `{"jsonrpc": "2.0", "method": "ping", "id": 1}`.

From Python, jsonrpcclient's
[websockets example](https://bensynapse.github.io/jsonrpcclient/transports/websockets/)
calls this server.
