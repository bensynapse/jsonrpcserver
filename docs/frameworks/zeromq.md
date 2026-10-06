---
description: A JSON-RPC 2.0 server over ZeroMQ with pyzmq and jsonrpcserver, sync and asyncio, with a message size limit and max_batch_size set. Tested in CI.
---

# ZeroMQ

Using [pyzmq](https://pyzmq.readthedocs.io/) with a REP socket, which
answers one request at a time.

## Sync

```python
--8<-- "docs/examples/zeromq_server.py"
```

## asyncio

With pyzmq's `zmq.asyncio`:

```python
--8<-- "docs/examples/zeromq_async_server.py"
```

## Notes

A REP socket must send a reply for every message it receives, before it can
receive the next one. So a notification gets an empty message back, which
the client should ignore.

`MAXMSGSIZE` makes ZeroMQ drop a client that sends a bigger message. There's
no limit by default. `max_batch_size` limits how many requests one batch can
hold. See [Security](../security.md).

The examples bind to `127.0.0.1`. `tcp://*:8000` would listen on every
network interface, and ZeroMQ has no authentication unless you set up one of
its security mechanisms, such as CURVE.

## Try it

Install pyzmq (`pip install pyzmq`) and run one of the examples. From Python,
jsonrpcclient's
[ZeroMQ example](https://bensynapse.github.io/jsonrpcclient/transports/zeromq/)
calls this server.
