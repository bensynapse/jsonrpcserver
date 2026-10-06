from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from jsonrpcserver import Result, Success, dispatch, method


@method
def ping() -> Result:
    return Success("pong")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers["Content-Length"])
        response = dispatch(self.rfile.read(length).decode())
        if response:
            body = response.encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            # A notification. There's nothing to send back.
            self.send_response(204)
            self.end_headers()


if __name__ == "__main__":
    ThreadingHTTPServer(("localhost", 5000), Handler).serve_forever()
