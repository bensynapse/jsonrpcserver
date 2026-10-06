---
description: Give jsonrpcserver methods the HTTP request, the logged-in user or a database session through context, with examples for Flask, FastAPI and Django.
---

# Context

Methods often need something from the server that the client mustn't control:
the logged-in user, the HTTP request, a database session. Pass it as
`context`. It becomes the first argument of every method, and the client can't
see or change it.

A small class keeps the context tidy when there's more than one thing to pass:

```python
from dataclasses import dataclass
from typing import Any

from jsonrpcserver import Result, Success, dispatch


@dataclass
class Context:
    user: str
    request: Any


def whoami(context: Context) -> Result:
    return Success(context.user)


def user_for(authorization: str) -> str:
    # Look the token up in your user store. This is a stand-in.
    return {"Bearer abc123": "beau"}.get(authorization, "anonymous")


METHODS = {"whoami": whoami}
```

The method's other parameters come after `context`, and the request's
`params` fill those as usual.

## Flask

<!-- requires: flask -->
```python
from flask import Flask, Response, request

app = Flask(__name__)


@app.post("/")
def index() -> Response:
    context = Context(user_for(request.headers.get("Authorization", "")), request)
    if response := dispatch(
        request.get_data(as_text=True), METHODS, context=context, max_batch_size=100
    ):
        return Response(response, content_type="application/json")
    return Response(status=204)
```

Trying it with Flask's test client:

<!-- requires: flask -->
```pycon
>>> client = app.test_client()
>>> client.post(
...     "/",
...     data='{"jsonrpc": "2.0", "method": "whoami", "id": 1}',
...     headers={"Authorization": "Bearer abc123"},
... ).get_data(as_text=True)
'{"jsonrpc": "2.0", "result": "beau", "id": 1}'
```

## FastAPI

<!-- requires: fastapi -->
```python
from fastapi import FastAPI, Request
from fastapi import Response as FastAPIResponse

from jsonrpcserver import async_dispatch

api = FastAPI()


@api.post("/")
async def endpoint(request: Request) -> FastAPIResponse:
    context = Context(user_for(request.headers.get("Authorization", "")), request)
    body = (await request.body()).decode()
    if response := await async_dispatch(
        body, METHODS, context=context, max_batch_size=100
    ):
        return FastAPIResponse(response, media_type="application/json")
    return FastAPIResponse(status_code=204)
```

`async_dispatch` calls the plain `whoami` method too. To try it, FastAPI's
test client needs [httpx2](https://pypi.org/project/httpx2/):

<!-- requires: httpx2 -->
```pycon
>>> from fastapi.testclient import TestClient
>>> TestClient(api).post(
...     "/",
...     content='{"jsonrpc": "2.0", "method": "whoami", "id": 1}',
...     headers={"Authorization": "Bearer abc123"},
... ).text
'{"jsonrpc": "2.0", "result": "beau", "id": 1}'
```

FastAPI's `Depends` doesn't reach into methods, because jsonrpcserver calls
them, not FastAPI. Resolve what you need in the endpoint, as above, and pass
it in the context.

## Django

<!-- requires: django -->
```python
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def jsonrpc(request: HttpRequest) -> HttpResponse:
    # With Django's authentication, use request.user instead of user_for.
    context = Context(user_for(request.headers.get("Authorization", "")), request)
    if response := dispatch(
        request.body.decode(), METHODS, context=context, max_batch_size=100
    ):
        return HttpResponse(response, content_type="application/json")
    return HttpResponse(status=204)
```

## A database session per request

Open the session in the view, pass it in the context, and close it when
`dispatch` returns. Every method in a batch then shares the one session:

```python
from contextlib import closing
import sqlite3


def count_users(context: sqlite3.Connection) -> Result:
    (count,) = context.execute("SELECT count(*) FROM users").fetchone()
    return Success(count)


def handle(request_body: str) -> str:
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute("CREATE TABLE users (name TEXT)")  # Stand-in for a real database.
        return dispatch(
            request_body, {"count_users": count_users}, context=db, max_batch_size=100
        )
```

```pycon
>>> handle('{"jsonrpc": "2.0", "method": "count_users", "id": 1}')
'{"jsonrpc": "2.0", "result": 0, "id": 1}'
```

With `async_dispatch`, the requests in a batch run concurrently. Make sure the
shared object can be used that way, or open what you need in each method.
