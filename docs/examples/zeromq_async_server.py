import asyncio

import zmq
import zmq.asyncio

from jsonrpcserver import Result, Success, async_dispatch, method


@method
async def ping() -> Result:
    return Success("pong")


async def main() -> None:
    socket = zmq.asyncio.Context().socket(zmq.REP)
    # A bigger message disconnects the client. The default is no limit.
    socket.setsockopt(zmq.MAXMSGSIZE, 1_000_000)
    socket.bind("tcp://127.0.0.1:8000")
    while True:
        request = await socket.recv_string()
        # max_batch_size: see the Security page.
        await socket.send_string(await async_dispatch(request, max_batch_size=100))


if __name__ == "__main__":
    asyncio.run(main())
