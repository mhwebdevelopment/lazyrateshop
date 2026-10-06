"""
Test fixtures spin up a real local HTTP server (not a mock object) so
Provider.fetch() implementations exercise actual network I/O over
loopback. Delays and error responses are produced by the server itself
responding slowly or with error status codes -- not by fabricated data
returned in-process.
"""
import asyncio
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

import pytest


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class DelayedHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        params = dict(p.split("=") for p in self.path.split("?", 1)[1].split("&")) if "?" in self.path else {}
        delay_ms = int(params.get("delay_ms", "0"))
        fail = params.get("fail", "0") == "1"
        time.sleep(delay_ms / 1000)
        if fail:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"error")
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")


@pytest.fixture(scope="session")
def http_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), DelayedHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
