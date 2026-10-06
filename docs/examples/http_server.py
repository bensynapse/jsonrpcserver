import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from jsonrpcserver import Result, Success, dispatch, method

MAX_BODY = 1_000_000  # bytes


@method
def ping() -> Result:
    return Success("pong")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = self.headers.get("Content-Length", "")
        if not length.isdecimal():
            self.send_error(411, "Content-Length required")
            return
        if int(length) > MAX_BODY:
            self.send_error(413, "Request body too large")
            return
        try:
            request = self.rfile.read(int(length)).decode("utf-8")
        except UnicodeDecodeError:
            response = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Parse error"},
                    "id": None,
                }
            )
        else:
            # max_batch_size: see the Security page.
            response = dispatch(request, max_batch_size=100)
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
    ThreadingHTTPServer(("localhost", 8000), Handler).serve_forever()
