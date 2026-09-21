"""Smoke-test the authenticated NestJS/Nginx Copilot SSE path.

The bearer token is read from ``IPLMS_SMOKE_BEARER_TOKEN`` so it does not need
to appear in shell history or process arguments.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def smoke(url: str, question: str, parking_lot_id: str | None, timeout: float) -> int:
    token = os.getenv("IPLMS_SMOKE_BEARER_TOKEN", "").strip()
    if not token:
        print("Thiếu IPLMS_SMOKE_BEARER_TOKEN.", file=sys.stderr)
        return 2

    payload: dict[str, str] = {"query": question}
    if parking_lot_id:
        payload["parkingLotId"] = parking_lot_id
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/event-stream" not in content_type:
                print(f"Sai Content-Type: {content_type}", file=sys.stderr)
                return 1

            seen: list[str] = []
            text_parts: list[str] = []
            event_name = "message"
            data_lines: list[str] = []

            def flush() -> bool:
                nonlocal event_name, data_lines
                if not data_lines:
                    event_name = "message"
                    return False
                data = json.loads("\n".join(data_lines))
                event_type = data.get("type") or event_name
                seen.append(event_type)
                if event_type == "text.delta":
                    delta = data.get("delta", "")
                    text_parts.append(delta)
                    print(delta, end="", flush=True)
                elif event_type == "error":
                    error = data.get("error") or {}
                    raise RuntimeError(error.get("message", "SSE error"))
                event_name = "message"
                data_lines = []
                return event_type == "done"

            completed = False
            for raw_line in response:
                line = raw_line.decode("utf-8").rstrip("\r\n")
                if not line:
                    completed = flush() or completed
                    if completed:
                        break
                elif line.startswith("event:"):
                    event_name = line[6:].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
            if data_lines:
                completed = flush() or completed

            print()
            required = {"start", "done"}
            if not required.issubset(seen) or not text_parts:
                print(f"Stream chưa hoàn chỉnh; events={seen}", file=sys.stderr)
                return 1
            print(f"[OK] SSE events={seen} chars={len(''.join(text_parts))}")
            return 0
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {body[:1000]}", file=sys.stderr)
    except (URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Smoke test thất bại: {exc}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test Copilot POST SSE")
    parser.add_argument(
        "--url",
        default="http://localhost:3000/api/v1/ai/copilot/stream",
    )
    parser.add_argument(
        "--question",
        default="Hai giờ đầu gửi ô tô ở Landmark 81 giá bao nhiêu?",
    )
    parser.add_argument("--parking-lot-id", default="lot_landmark_81")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()
    return smoke(args.url, args.question, args.parking_lot_id or None, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
