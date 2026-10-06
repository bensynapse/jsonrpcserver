import uvicorn
from fastapi import FastAPI, Request, Response

from jsonrpcserver import Result, Success, async_dispatch, method

app = FastAPI()


@method
async def ping() -> Result:
    return Success("pong")


@app.post("/")
async def index(request: Request) -> Response:
    if response := await async_dispatch((await request.body()).decode()):
        return Response(response, media_type="application/json")
    return Response(status_code=204)


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=5000)
