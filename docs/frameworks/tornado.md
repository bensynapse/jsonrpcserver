---
description: A JSON-RPC 2.0 server with Tornado and jsonrpcserver's async_dispatch, with a request size limit and max_batch_size set. Tested in CI.
---

# Tornado

```python
--8<-- "docs/examples/tornado_server.py"
```

Tornado refuses a body bigger than `max_body_size` with 400. Its default is
100 MB, so the example passes a smaller one to `listen`. `max_batch_size`
limits how many requests one batch can hold. See [Security](../security.md).

To give methods the request, pass `self.request` as `context`. See
[Context](../context.md).

## Try it

Save the example as `tornado_server.py`, install Tornado (`pip install tornado`), and run it:

```sh
python tornado_server.py
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
