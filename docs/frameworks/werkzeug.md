---
description: A JSON-RPC 2.0 server with Werkzeug and jsonrpcserver, with a request size limit and max_batch_size set. Tested in CI.
---

# Werkzeug

[Werkzeug](https://werkzeug.palletsprojects.com/) is the WSGI toolkit under
Flask. Use it on its own for a small WSGI app:

```python
--8<-- "docs/examples/werkzeug_server.py"
```

Setting `max_content_length` on a `Request` subclass makes `get_data` refuse
a bigger body with 413. `max_batch_size` limits how many requests one batch
can hold. See [Security](../security.md).

To give methods the request, pass it as `context`:
`dispatch(..., context=request)`. See [Context](../context.md).

`run_simple` is Werkzeug's development server. For production, use a WSGI
server such as Gunicorn.

## Try it

Save the example as `werkzeug_server.py`, install Werkzeug (`pip install werkzeug`), and run it:

```sh
python werkzeug_server.py
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
