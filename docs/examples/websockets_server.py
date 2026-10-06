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
        if response := await async_dispatch(request):
            await websocket.send(response)


async def main() -> None:
    async with serve(handler, "localhost", 5000) as server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
