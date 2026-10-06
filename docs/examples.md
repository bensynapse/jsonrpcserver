# Examples

jsonrpcserver doesn't listen on a port itself. You receive the request with a
framework or transport library, pass it to `dispatch` or `async_dispatch`, and
send back the result. Each example below answers `ping` with `pong` on
`localhost:5000`. CI starts every one of them and sends it real requests.

For HTTP, send status 204 with an empty body when `dispatch` gives an empty
string. That means the request was a notification. With websockets and most
message queues, you can send nothing at all.

The libraries' own docs cover running them in production.

## http.server

Python's built-in HTTP server, with no other dependencies:

```python
--8<-- "docs/examples/http_server.py"
```

jsonrpcserver also has a small built-in server, `serve()`. It's for trying
things out, not for production:

```python
--8<-- "docs/examples/serve.py"
```

## Flask

```python
--8<-- "docs/examples/flask_server.py"
```

## Werkzeug

```python
--8<-- "docs/examples/werkzeug_server.py"
```

## Django

A whole Django project in one file. In your project, the view goes in an app
and the URL pattern in its `urls.py`.

```python
--8<-- "docs/examples/django_server.py"
```

## FastAPI

```python
--8<-- "docs/examples/fastapi_server.py"
```

## aiohttp

```python
--8<-- "docs/examples/aiohttp_server.py"
```

## Sanic

```python
--8<-- "docs/examples/sanic_server.py"
```

## Tornado

```python
--8<-- "docs/examples/tornado_server.py"
```

## websockets

Uses the `websockets.asyncio` server from websockets 13 and later.

```python
--8<-- "docs/examples/websockets_server.py"
```

## ZeroMQ

Using [pyzmq](https://pyzmq.readthedocs.io/):

```python
--8<-- "docs/examples/zeromq_server.py"
```

With asyncio, using pyzmq's `zmq.asyncio`:

```python
--8<-- "docs/examples/zeromq_async_server.py"
```

## Socket.IO

Using [Flask-SocketIO](https://flask-socketio.readthedocs.io/):

```python
--8<-- "docs/examples/socketio_server.py"
```
