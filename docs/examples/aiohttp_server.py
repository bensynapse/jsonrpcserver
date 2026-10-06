from aiohttp import web

from jsonrpcserver import Result, Success, async_dispatch, method


@method
async def ping() -> Result:
    return Success("pong")


async def handle(request: web.Request) -> web.Response:
    if response := await async_dispatch(await request.text()):
        return web.Response(text=response, content_type="application/json")
    return web.Response(status=204)


app = web.Application()
app.router.add_post("/", handle)

if __name__ == "__main__":
    web.run_app(app, host="localhost", port=5000)
