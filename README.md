<p align="center">
  <a href="https://pypi.org/project/jsonrpcserver/"><img src="https://img.shields.io/pypi/v/jsonrpcserver.svg" alt="PyPI" /></a>
  <a href="https://github.com/bensynapse/jsonrpcserver/actions/workflows/ci.yml"><img src="https://github.com/bensynapse/jsonrpcserver/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <img src="https://img.shields.io/pypi/pyversions/jsonrpcserver" alt="Python versions" />
  <img src="https://img.shields.io/pypi/dw/jsonrpcserver" alt="Downloads" />
  <img src="https://img.shields.io/github/license/bensynapse/jsonrpcserver" alt="License" />
</p>

<p align="center">
  <img alt="Jsonrpcserver Logo" src="https://raw.githubusercontent.com/bensynapse/jsonrpcserver/main/logo.png" />
</p>

<p align="center">
  <i>Process incoming JSON-RPC requests in Python</i>
</p>

<p align="center">
  <a href="https://bensynapse.github.io/jsonrpcserver/">Documentation</a> |
  <a href="https://bensynapse.github.io/jsonrpcserver/examples/">Examples</a> |
  <a href="https://github.com/bensynapse/jsonrpcserver/blob/main/CHANGELOG.md">Changelog</a>
</p>

https://github.com/user-attachments/assets/94fb4f04-a5f1-41ca-84dd-7e18b87990e0

## Installation

```sh
pip install jsonrpcserver
```

It supports Python 3.8 and later.

## Usage

```python
from jsonrpcserver import Result, Success, dispatch, method


@method
def ping() -> Result:
    return Success("pong")
```

```python
>>> dispatch('{"jsonrpc": "2.0", "method": "ping", "id": 1}')
'{"jsonrpc": "2.0", "result": "pong", "id": 1}'
```

jsonrpcserver doesn't listen on a port itself. The
[examples](https://bensynapse.github.io/jsonrpcserver/examples/) show it with
Flask, FastAPI, Django, aiohttp, websockets, ZeroMQ and more.

Before you expose a server to the internet, read the
[security notes](https://bensynapse.github.io/jsonrpcserver/security/).

## Documentation

Full documentation is at
[bensynapse.github.io/jsonrpcserver](https://bensynapse.github.io/jsonrpcserver/).

## See also

- [jsonrpcclient](https://github.com/bensynapse/jsonrpcclient): create JSON-RPC requests and parse responses in Python
