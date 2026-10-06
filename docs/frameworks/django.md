---
description: A JSON-RPC 2.0 endpoint in Django with jsonrpcserver, as a whole project in one file, with a request size limit and max_batch_size set. Tested in CI.
---

# Django

A whole Django project in one file. In your project, the view goes in an app
and the URL pattern in its `urls.py`.

```python
--8<-- "docs/examples/django_server.py"
```

Django refuses a body bigger than `DATA_UPLOAD_MAX_MEMORY_SIZE` with 400 Bad
Request when the view reads `request.body`. The default is 2.5 MB, and the
example sets it explicitly. `max_batch_size` limits how many requests one
batch can hold. See [Security](../security.md).

The view is exempt from CSRF checks, because JSON-RPC clients don't send a
CSRF token. Use another way to authenticate them, such as a token in a header.
To give methods `request.user`, pass it in the context.
[Context](../context.md#django) has an example.

`runserver` is Django's development server. For production, use a WSGI or
ASGI server, as the
[Django docs](https://docs.djangoproject.com/en/stable/howto/deployment/)
describe.

## Try it

Save the example as `django_server.py`, install Django (`pip install django`), and run it:

```sh
python django_server.py
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
