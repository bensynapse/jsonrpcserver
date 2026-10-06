---
description: A JSON-RPC 2.0 server with Sanic and jsonrpcserver's async_dispatch, with a request size limit and max_batch_size set. Tested in CI.
---

# Sanic

```python
--8<-- "docs/examples/sanic_server.py"
```

Sanic refuses a body bigger than `REQUEST_MAX_SIZE` with 413. Its default is
100 MB, so the example sets a smaller one. `max_batch_size` limits how many
requests one batch can hold. See [Security](../security.md).

To give methods the request, pass it as `context`:
`await async_dispatch(..., context=request)`. See [Context](../context.md).

`single_process=True` keeps the example simple. Sanic's own docs cover
running it with workers in production.

## Try it

Save the example as `sanic_server.py`, install Sanic (`pip install sanic`), and run it:

```sh
python sanic_server.py
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
