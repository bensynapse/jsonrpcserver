---
description: A JSON-RPC 2.0 server with aiohttp and jsonrpcserver's async_dispatch, with a request size limit and max_batch_size set. Tested in CI.
---

# aiohttp

```python
--8<-- "docs/examples/aiohttp_server.py"
```

aiohttp refuses a body bigger than `client_max_size` with 413. Its default is
1 MiB, and the example sets it explicitly so it's easy to change.
`max_batch_size` limits how many requests one batch can hold. See
[Security](../security.md).

To give methods the request, pass it as `context`:
`await async_dispatch(..., context=request)`. See [Context](../context.md).

## Try it

Save the example as `aiohttp_server.py`, install aiohttp (`pip install aiohttp`), and run it:

```sh
python aiohttp_server.py
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
