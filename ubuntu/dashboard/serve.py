"""Serve the read-only dashboard and the local controller API on one origin."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener


ROOT = Path(__file__).resolve().parent
LOCAL = build_opener(ProxyHandler({}))
ASSETS = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
          "/style.css": ("style.css", "text/css")}
ENDPOINTS = {"topology": "topology", "hosts": "sdn/hosts",
             "bandwidth": "sdn/bandwidth", "flows": "flows"}


class Dashboard(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/snapshot":
            try:
                data = {}
                for key, path in ENDPOINTS.items():
                    with LOCAL.open("http://127.0.0.1:8080/" + path, timeout=2) as reply:
                        data[key] = json.load(reply)
            except (URLError, OSError, ValueError):
                self.send_error(502, "Controller API unavailable")
                return
            body = json.dumps(data).encode()
            mime = "application/json"
        elif self.path in ASSETS:
            filename, mime = ASSETS[self.path]
            body = (ROOT / filename).read_bytes()
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    with ThreadingHTTPServer(("127.0.0.1", 8081), Dashboard) as server:
        print("Dashboard: http://127.0.0.1:8081", flush=True)
        server.serve_forever()
