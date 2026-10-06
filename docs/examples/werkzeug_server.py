from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response

from jsonrpcserver import Result, Success, dispatch, method


@method
def ping() -> Result:
    return Success("pong")


@Request.application
def application(request: Request) -> Response:
    if response := dispatch(request.get_data(as_text=True)):
        return Response(response, content_type="application/json")
    return Response(status=204)


if __name__ == "__main__":
    run_simple("localhost", 5000, application)
