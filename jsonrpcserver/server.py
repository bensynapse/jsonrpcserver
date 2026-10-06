"""A development server for trying out methods, built on Python's http.server.

It's meant for trying things out. For production, put dispatch behind a real web
server or framework.
"""

import json
import logging
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .main import dispatch
from .response import ParseErrorResponse, to_error_dict

logger = logging.getLogger(__name__)


class RequestHandler(BaseHTTPRequestHandler):
    """Handle HTTP requests"""

    def log_message(self, format: str, *args: Any) -> None:
        """Log through the logging module instead of writing to sys.stderr.

        sys.stderr is None in some environments, such as a PyInstaller app built with
        --noconsole. Writing to it there raised an exception that dropped every
        connection without a response (#269).
        """
        logger.info("%s - %s", self.address_string(), format % args)

    def do_POST(self) -> None:
        """Handle POST request"""
        try:
            length = int(self.headers["Content-Length"])
        except TypeError:
            self.send_error(411, "Content-Length required")
            return
        except ValueError:
            self.send_error(400, "Invalid Content-Length")
            return
        if length < 0:
            self.send_error(400, "Invalid Content-Length")
            return
        body = self.rfile.read(length)
        try:
            request = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            response = json.dumps(to_error_dict(ParseErrorResponse(str(exc))))
        else:
            response = dispatch(request)
        if response:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response.encode())))
            self.end_headers()
            self.wfile.write(response.encode())
        else:
            # A notification, or a batch of only notifications. There's nothing to send.
            self.send_response(204)
            self.end_headers()


def listening_message(name: str, port: int) -> str:
    """The line serve() shows when it starts."""
    if name in ("", "0.0.0.0"):
        return (
            f" * Listening on port {port} on every network interface. This is a "
            'development server. Use serve("localhost", ...) to accept only local '
            "connections."
        )
    return f" * Listening on http://{name}:{port}/. This is a development server."


def serve(name: str = "", port: int = 5000) -> None:
    """Serve the methods registered with `@method` over HTTP. For development only.

    It answers POST requests on any path with `dispatch`, sends 204 No Content for a
    notification, and runs each request in its own thread. It runs until the process
    is stopped, for example with Ctrl+C.

    When it starts, it logs where it's listening on the `jsonrpcserver.server`
    logger. If logging isn't configured, it writes that line to stderr instead
    (new in 5.0.10). Each request is logged at INFO level.

    It has no TLS, no authentication and no request size limit, and it doesn't pass
    `max_batch_size`. Put `dispatch` behind a real web server or framework in
    production.

    Args:
        name: The host name or address to listen on. The default, "", listens on
            every network interface, so other machines can connect. Pass "localhost"
            to accept only local connections.
        port: The port to listen on.

    Example:
        ```python
        from jsonrpcserver import Result, Success, method, serve

        @method
        def ping() -> Result:
            return Success("pong")

        serve("localhost", 8000)
        ```
    """
    httpd = ThreadingHTTPServer((name, port), RequestHandler)
    try:
        message = listening_message(name, port)
        logger.info("%s", message)
        if not logger.hasHandlers() and sys.stderr is not None:
            # logging isn't configured, so the line above went nowhere.
            print(message, file=sys.stderr, flush=True)
        httpd.serve_forever()
    finally:
        httpd.server_close()
