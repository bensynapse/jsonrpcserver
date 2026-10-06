from jsonrpcserver import Result, Success, method, serve


@method
def ping() -> Result:
    return Success("pong")


if __name__ == "__main__":
    serve("localhost", 8000)
