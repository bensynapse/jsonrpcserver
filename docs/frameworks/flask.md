---
description: A JSON-RPC 2.0 server with Flask and jsonrpcserver, with a request size limit and max_batch_size set. Tested in CI.
---

# Flask

```python
--8<-- "docs/examples/flask_server.py"
```

`MAX_CONTENT_LENGTH` makes Flask answer a bigger body with 413 before it's
read. Flask has no limit by default. `max_batch_size` limits how many
requests one batch can hold. See [Security](../security.md).

To give methods the request or the logged-in user, pass `context`.
[Context](../context.md#flask) has a Flask example.

`app.run` starts Flask's development server. For production, run the app with
a WSGI server such as Gunicorn, as the
[Flask docs](https://flask.palletsprojects.com/en/stable/deploying/) describe.

## Try it

Save the example as `flask_server.py`, install Flask (`pip install flask`), and run it:

```sh
python flask_server.py
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
