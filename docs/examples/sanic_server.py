from sanic import HTTPResponse, Request, Sanic

from jsonrpcserver import Result, Success, async_dispatch, method

app = Sanic("jsonrpc")


@method
async def ping() -> Result:
    return Success("pong")


@app.post("/")
async def index(request: Request) -> HTTPResponse:
    if response := await async_dispatch(request.body.decode()):
        return HTTPResponse(response, content_type="application/json")
    return HTTPResponse(status=204)


if __name__ == "__main__":
    app.run(host="localhost", port=5000, single_process=True)
