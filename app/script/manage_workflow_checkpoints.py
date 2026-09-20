"""Setup, inspect and prune the PostgreSQL LangGraph checkpoint store."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.core.exceptions import WorkflowConfigurationError
from app.infra.workflow import (
    inspect_checkpoint_store,
    open_workflow_checkpointer,
    prune_expired_checkpoint_threads,
)


async def run(args: argparse.Namespace) -> int:
    try:
        if args.command == "setup":
            async with open_workflow_checkpointer(
                backend="postgres",
                setup_schema=True,
            ):
                pass
            report = await inspect_checkpoint_store()
        elif args.command == "check":
            report = await inspect_checkpoint_store()
        else:
            report = await prune_expired_checkpoint_threads(
                retention_days=args.retention_days,
                batch_size=args.batch_size,
                apply=args.apply,
            )
    except WorkflowConfigurationError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    except Exception:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "Thao tác PostgreSQL checkpoint thất bại; không in chi tiết kết nối.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    print(json.dumps({"ok": True, **report}, ensure_ascii=False, indent=2))
    return 0 if report.get("ready", True) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Vận hành PostgreSQL checkpoint store của LangGraph"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("setup", help="Tạo schema và chạy migration LangGraph")
    subparsers.add_parser("check", help="Kiểm tra schema, bảng và migration")
    prune = subparsers.add_parser("prune", help="Liệt kê hoặc xóa thread quá retention")
    prune.add_argument("--retention-days", type=int)
    prune.add_argument("--batch-size", type=int)
    prune.add_argument(
        "--apply",
        action="store_true",
        help="Thực sự xóa; nếu thiếu cờ này lệnh chỉ dry-run",
    )
    return parser


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")
    operation = run(build_parser().parse_args())
    if sys.platform == "win32":
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            return runner.run(operation)
    return asyncio.run(operation)


if __name__ == "__main__":
    raise SystemExit(main())
