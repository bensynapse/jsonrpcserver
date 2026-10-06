from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response

from jsonrpcserver import Result, Success, dispatch, method


class JsonRpcRequest(Request):
    # Bigger requests get 413 Request Entity Too Large.
    max_content_length = 1_000_000


@method
def ping() -> Result:
    return Success("pong")


@JsonRpcRequest.application
def application(request: JsonRpcRequest) -> Response:
    # max_batch_size: see the Security page.
    if response := dispatch(request.get_data(as_text=True), max_batch_size=100):
        return Response(response, content_type="application/json")
    return Response(status=204)


if __name__ == "__main__":
    run_simple("localhost", 8000, application)
