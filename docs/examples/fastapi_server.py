import uvicorn
from fastapi import FastAPI, Request, Response

from jsonrpcserver import Result, Success, async_dispatch, method

MAX_BODY = 1_000_000  # bytes

app = FastAPI()


@method
async def ping() -> Result:
    return Success("pong")


@app.post("/")
async def index(request: Request) -> Response:
    # FastAPI has no limit on the body size, so read it in chunks and stop
    # when it gets too big.
    body = b""
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_BODY:
            return Response(status_code=413)
    # max_batch_size: see the Security page.
    if response := await async_dispatch(body.decode(), max_batch_size=100):
        return Response(response, media_type="application/json")
    return Response(status_code=204)


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
