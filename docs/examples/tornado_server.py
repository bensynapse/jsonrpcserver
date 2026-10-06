import asyncio

from tornado import web

from jsonrpcserver import Result, Success, async_dispatch, method


@method
async def ping() -> Result:
    return Success("pong")


class MainHandler(web.RequestHandler):
    async def post(self) -> None:
        # max_batch_size: see the Security page.
        request = self.request.body.decode()
        if response := await async_dispatch(request, max_batch_size=100):
            self.set_header("Content-Type", "application/json")
            self.write(response)
        else:
            self.set_status(204)


async def main() -> None:
    app = web.Application([(r"/", MainHandler)])
    # Tornado's default limit is 100 MB.
    app.listen(8000, address="localhost", max_body_size=1_000_000)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
