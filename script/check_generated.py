#!/usr/bin/env python3
"""PR không được sửa file sinh tự động (IPLMS ADR-0060); chỉ CI trên develop ghi chúng.

Bản giống hệt ở gốc IPLMS và 6 repo con. Đọc diff `<base>...HEAD`, không chạy gì từ metadata PR.
  python -X utf8 script/check_generated.py --base origin/develop [--branch <tên nhánh PR>]
Nhánh việc vặt tháng được sinh lại issue-registry.md cho tới khi CI có SUBMODULES_TOKEN (bug-048).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

GENERATED = ("docs/projects/BOARD.md", "docs/projects/issue-registry.md")
REGISTRY_BRANCH = re.compile(r"chore/CHORE-\d{3}-\d{4}-\d{2}-monthly-maintenance\Z")


def changed_files(base: str) -> list[str]:
    p = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if p.returncode:
        raise SystemExit(f"check_generated: không đọc được diff {base}...HEAD: {p.stderr.strip()}")
    return p.stdout.split()


def violations(files: list[str], branch: str) -> list[str]:
    hit = [f for f in files if f in GENERATED]
    if REGISTRY_BRANCH.match(branch):
        hit = [f for f in hit if f != "docs/projects/issue-registry.md"]
    return hit


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="origin/develop")
    ap.add_argument("--branch", default=os.environ.get("GITHUB_HEAD_REF", ""))
    args = ap.parse_args()
    hit = violations(changed_files(args.base), args.branch)
    if not hit:
        print("check_generated: PR không sửa file sinh tự động")
        return 0
    print("check_generated: PR sửa file chỉ CI được ghi (ADR-0060). Đổi trạng thái/người nhận/hạn ở Meta hồ sơ, rồi trả file về:")
    for f in hit:
        print(f"  git checkout {args.base} -- {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
