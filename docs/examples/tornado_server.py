import asyncio

from tornado import web

from jsonrpcserver import Result, Success, async_dispatch, method


@method
async def ping() -> Result:
    return Success("pong")


class MainHandler(web.RequestHandler):
    async def post(self) -> None:
        if response := await async_dispatch(self.request.body.decode()):
            self.set_header("Content-Type", "application/json")
            self.write(response)
        else:
            self.set_status(204)


async def main() -> None:
    app = web.Application([(r"/", MainHandler)])
    app.listen(5000, address="localhost")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
