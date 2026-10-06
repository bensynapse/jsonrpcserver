---
description: A JSON-RPC 2.0 endpoint in FastAPI with jsonrpcserver's async_dispatch, with a request size limit and max_batch_size set. Tested in CI.
---

# FastAPI

```python
--8<-- "docs/examples/fastapi_server.py"
```

FastAPI and Starlette have no limit on the body size, so the endpoint reads
the body in chunks and answers 413 once it's too big. Many deployments also
set a limit in the reverse proxy in front, such as nginx's
`client_max_body_size`. `max_batch_size` limits how many requests one batch
can hold. See [Security](../security.md).

The methods are `async`, and the endpoint uses `async_dispatch`. Plain methods
work too, but they run on the event loop, so a slow one holds up other
requests. See [Async](../async.md).

FastAPI's dependency injection doesn't reach into methods. Resolve what they
need in the endpoint and pass it as `context`.
[Context](../context.md#fastapi) has an example.

## Try it

Save the example as `fastapi_server.py`, install FastAPI and Uvicorn (`pip install fastapi uvicorn`), and run it:

```sh
python fastapi_server.py
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
