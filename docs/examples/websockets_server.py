import asyncio

from websockets.asyncio.server import ServerConnection, serve

from jsonrpcserver import Result, Success, async_dispatch, method


@method
async def ping() -> Result:
    return Success("pong")


async def handler(websocket: ServerConnection) -> None:
    async for message in websocket:
        request = message.decode() if isinstance(message, bytes) else message
        # Unlike HTTP, there's no need to answer a notification.
        # max_batch_size: see the Security page.
        if response := await async_dispatch(request, max_batch_size=100):
            await websocket.send(response)


async def main() -> None:
    # A bigger message closes the connection. The default is 1 MiB.
    async with serve(handler, "localhost", 8000, max_size=1_000_000) as server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
