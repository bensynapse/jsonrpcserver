"""A simple development server for serving JSON-RPC requests using Python's builtin
http.server module.

It's meant for trying things out. For production, put dispatch behind a real web
server or framework.
"""

import json
import logging
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


def serve(name: str = "", port: int = 5000) -> None:
    """A simple function to serve HTTP requests. For development only."""
    logger.info(" * Listening on port %s", port)
    httpd = ThreadingHTTPServer((name, port), RequestHandler)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
