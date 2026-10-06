"""A simple development server for serving JSON-RPC requests using Python's builtin
http.server module.
"""

import logging
from http.server import BaseHTTPRequestHandler, HTTPServer

from .main import dispatch


class RequestHandler(BaseHTTPRequestHandler):
    """Handle HTTP requests"""

    def do_POST(self) -> None:  # pylint: disable=invalid-name
        """Handle POST request"""
        response = dispatch(
            self.rfile.read(int(str(self.headers["Content-Length"]))).decode()
        )
        if response is not None:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(str(response).encode())


def serve(name: str = "", port: int = 5000) -> None:
    """A simple function to serve HTTP requests"""
    logging.info(" * Listening on port %s", port)
    HTTPServer((name, port), RequestHandler).serve_forever()
