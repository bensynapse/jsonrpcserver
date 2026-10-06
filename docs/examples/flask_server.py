from flask import Flask, Response, request

from jsonrpcserver import Result, Success, dispatch, method

app = Flask(__name__)


@method
def ping() -> Result:
    return Success("pong")


@app.post("/")
def index() -> Response:
    if response := dispatch(request.get_data(as_text=True)):
        return Response(response, content_type="application/json")
    return Response(status=204)


if __name__ == "__main__":
    app.run(port=5000)
