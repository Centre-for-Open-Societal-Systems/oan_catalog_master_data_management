"""Development-only OAuth token endpoint for the Docker consumer smoke test."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class TokenHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/token":
            self.send_error(404)
            return
        payload = json.dumps({"access_token": "consumer-smoke-token", "expires_in": 300}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self.send_response(204 if self.path == "/health" else 404)
        self.end_headers()

    def log_message(self, _format, *_args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), TokenHandler).serve_forever()
