"""Throw-away test server for verifying static/js/cl-ui.js in a real browser.

Serves the workspace statically and adds:
  POST /slow   -> sleeps 700ms then 200  (lets us observe the in-flight state)
  GET  /slow   -> sleeps 700ms then 200
  POST /ok     -> 200
  POST /fail   -> 500
Not part of the app; delete it whenever.
"""
import http.server
import socketserver
import time
import pathlib

ROOT = pathlib.Path(__file__).parent
PORT = 8777


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, *a):
        pass  # keep the console quiet

    def _respond(self, code, body=b'{"ok":true}', ctype='application/json'):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith('/slow'):
            time.sleep(0.7)
            return self._respond(200)
        return super().do_GET()

    def do_POST(self):
        length = int(self.headers.get('Content-Length') or 0)
        if length:
            self.rfile.read(length)
        if self.path.startswith('/hang'):
            time.sleep(10)          # never answers within a test run -> watchdog case
            return self._respond(200)
        if self.path.startswith('/slow'):
            time.sleep(0.7)
            return self._respond(200)
        if self.path.startswith('/fail'):
            return self._respond(500, b'{"ok":false}')
        return self._respond(200)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == '__main__':
    with Server(('127.0.0.1', PORT), Handler) as httpd:
        print(f'cl-ui test server on http://127.0.0.1:{PORT}/', flush=True)
        httpd.serve_forever()
