"""Supervise native REST and gRPC without mutating the shared Docker stack."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser


def commands(python: str, rest_port: int) -> list[list[str]]:
    return [
        [python, "-m", "app.grpc_server"],
        [python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(rest_port)],
    ]


def stop_children(children) -> None:
    for child in children:
        if child.poll() is None:
            child.terminate()
    for child in children:
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


def wait_ready(children, rest_port: int, grpc_port: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    # Native loopback requests must not use an inherited HTTP proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while time.monotonic() < deadline:
        if any(child.poll() is not None for child in children):
            raise RuntimeError("A REST/gRPC process exited before both transports were ready")
        try:
            with socket.create_connection(("127.0.0.1", grpc_port), timeout=0.5):
                pass
            with opener.open(f"http://127.0.0.1:{rest_port}/health", timeout=0.5) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.1)
    raise RuntimeError("REST/gRPC readiness timed out; check dependencies and model setup")


def supervise(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rest-port", type=int, default=8000)
    parser.add_argument("--grpc-port", type=int, default=50051)
    parser.add_argument("--ready-timeout", type=float, default=120)
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not all(1 <= p <= 65535 for p in (args.rest_port, args.grpc_port)) or args.rest_port == args.grpc_port:
        parser.error("REST/gRPC ports must be distinct and between 1 and 65535")
    if args.ready_timeout <= 0:
        parser.error("Readiness timeout must be positive")
    cmds = commands(sys.executable, args.rest_port)
    if args.dry_run:
        print(json.dumps({"commands": cmds, "host": "127.0.0.1", "grpc_port": args.grpc_port}))
        return 0
    for port in (args.rest_port, args.grpc_port):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                print(f"Port {port} is busy. Resolve the conflict explicitly; no existing process was stopped.", file=sys.stderr)
                return 1
    env = dict(os.environ)
    env.update(AI_FASTAPI_PORT=str(args.rest_port), AI_GRPC_PORT=str(args.grpc_port), AI_GRPC_BIND_HOST="127.0.0.1")
    children = []
    try:
        for cmd in cmds:
            children.append(subprocess.Popen(cmd, cwd=Path(__file__).resolve().parents[2], env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
        wait_ready(children, args.rest_port, args.grpc_port, args.ready_timeout)
        print(f"REST http://127.0.0.1:{args.rest_port} and gRPC 127.0.0.1:{args.grpc_port} are listening. DB/model readiness is separate.")
        if args.open_browser:
            webbrowser.open(f"http://127.0.0.1:{args.rest_port}/")
        while all(child.poll() is None for child in children):
            time.sleep(0.2)
        print("A REST/gRPC process exited; stopping its sibling.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        stop_children(children)


if __name__ == "__main__":
    raise SystemExit(supervise())
