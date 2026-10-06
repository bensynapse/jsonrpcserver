from flask import Flask, Response, request

from jsonrpcserver import Result, Success, dispatch, method

app = Flask(__name__)
# Bigger requests get 413 Request Entity Too Large.
app.config["MAX_CONTENT_LENGTH"] = 1_000_000


@method
def ping() -> Result:
    return Success("pong")


@app.post("/")
def index() -> Response:
    # max_batch_size: see the Security page.
    if response := dispatch(request.get_data(as_text=True), max_batch_size=100):
        return Response(response, content_type="application/json")
    return Response(status=204)


if __name__ == "__main__":
    app.run(host="localhost", port=8000)
