"""Synthetic browser fixture only: python -m test.developer_dashboard_preview.
No service startup, settings, env files, model/data files or provider calls.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PAYLOAD = '<img src=x onerror="globalThis.__injected=true"> <script>globalThis.__injected=true</script>'


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in {"/", "/dashboard", "/ui"}:
            body = (Path(__file__).parent.parent / "static/index.html").read_bytes()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers(); self.wfile.write(body)
        elif self.path == "/api/system/info":
            self.json_response({"scope":"SYNTHETIC TEST FIXTURE", "untrusted": PAYLOAD})
        else:
            self.send_error(404)

    def do_POST(self):
        # Synthetic payloads; never persist uploads or proxy requests.
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path == "/api/copilot/ask":
            self.json_response({"success":True,"data":[{"answer":PAYLOAD,"sources":[PAYLOAD],"confidence":0}]})
        elif self.path == "/api/knowledge/ingest":
            self.json_response({"success":False,"message":PAYLOAD},422)
        else:
            self.send_error(404)

    def json_response(self, obj, status=200):
        body=json.dumps(obj).encode()
        self.send_response(status); self.send_header("Content-Type","application/json")
        self.end_headers(); self.wfile.write(body)


if __name__ == "__main__":
    print("SYNTHETIC UI FIXTURE http://127.0.0.1:18765/dashboard", flush=True)
    HTTPServer(("127.0.0.1",18765),Handler).serve_forever()
