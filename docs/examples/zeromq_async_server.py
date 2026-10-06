import asyncio

import zmq
import zmq.asyncio

from jsonrpcserver import Result, Success, async_dispatch, method


@method
async def ping() -> Result:
    return Success("pong")


async def main() -> None:
    socket = zmq.asyncio.Context().socket(zmq.REP)
    socket.bind("tcp://*:5000")
    while True:
        request = await socket.recv_string()
        await socket.send_string(await async_dispatch(request))


if __name__ == "__main__":
    asyncio.run(main())
