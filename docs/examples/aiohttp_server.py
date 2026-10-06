from aiohttp import web

from jsonrpcserver import Result, Success, async_dispatch, method


@method
async def ping() -> Result:
    return Success("pong")


async def handle(request: web.Request) -> web.Response:
    # max_batch_size: see the Security page.
    if response := await async_dispatch(await request.text(), max_batch_size=100):
        return web.Response(text=response, content_type="application/json")
    return web.Response(status=204)


# Bigger requests get 413 Request Entity Too Large. The default is 1 MiB.
app = web.Application(client_max_size=1_000_000)
app.router.add_post("/", handle)

if __name__ == "__main__":
    web.run_app(app, host="localhost", port=8000)
