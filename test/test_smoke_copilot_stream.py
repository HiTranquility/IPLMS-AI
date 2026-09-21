import io
import json
import os
import threading
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer

from app.script.smoke_copilot_stream import smoke


class _SseHandler(BaseHTTPRequestHandler):
    request_payload = None

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        type(self).request_payload = json.loads(self.rfile.read(length))
        events = [
            {"type": "start", "version": "1", "runId": "r", "messageId": "m", "seq": 1},
            {
                "type": "text.delta",
                "version": "1",
                "runId": "r",
                "messageId": "m",
                "seq": 2,
                "delta": "Xin chao",
            },
            {"type": "done", "version": "1", "runId": "r", "messageId": "m", "seq": 3},
        ]
        body = "".join(
            f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


class CopilotStreamSmokeTest(unittest.TestCase):
    def test_posts_backend_contract_and_validates_stream(self):
        server = HTTPServer(("127.0.0.1", 0), _SseHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        previous = os.environ.get("IPLMS_SMOKE_BEARER_TOKEN")
        os.environ["IPLMS_SMOKE_BEARER_TOKEN"] = "test-token"
        try:
            output = io.StringIO()
            with redirect_stdout(output):
                result = smoke(
                    f"http://127.0.0.1:{server.server_port}/api/v1/ai/copilot/stream",
                    "Phi bao nhieu?",
                    "lot-a",
                    2,
                )
            self.assertEqual(0, result)
            self.assertEqual(
                {"query": "Phi bao nhieu?", "parkingLotId": "lot-a"},
                _SseHandler.request_payload,
            )
            self.assertIn("[OK] SSE", output.getvalue())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
            if previous is None:
                os.environ.pop("IPLMS_SMOKE_BEARER_TOKEN", None)
            else:
                os.environ["IPLMS_SMOKE_BEARER_TOKEN"] = previous


if __name__ == "__main__":
    unittest.main()
