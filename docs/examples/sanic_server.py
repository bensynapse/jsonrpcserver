from sanic import HTTPResponse, Request, Sanic

from jsonrpcserver import Result, Success, async_dispatch, method

app = Sanic("jsonrpc")
# Bigger requests get 413 Request Entity Too Large. Sanic's default is 100 MB.
app.config.REQUEST_MAX_SIZE = 1_000_000


@method
async def ping() -> Result:
    return Success("pong")


@app.post("/")
async def index(request: Request) -> HTTPResponse:
    # max_batch_size: see the Security page.
    if response := await async_dispatch(request.body.decode(), max_batch_size=100):
        return HTTPResponse(response, content_type="application/json")
    return HTTPResponse(status=204)


if __name__ == "__main__":
    app.run(host="localhost", port=8000, single_process=True)
