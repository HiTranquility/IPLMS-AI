#!/usr/bin/env python3
"""Sinh danh mục UC trong docs/projects/usecases/README.md từ chính các file UC (IPLMS ADR-0065).

Bảng nằm giữa hai dấu `<!-- uc-index:start -->` / `<!-- uc-index:end -->`; phần còn lại của README giữ nguyên.
Cột lấy từ tiêu đề và Meta của từng `UC-NNN-*.md`: Trạng thái, Module (`Module / domain` hoặc `Module / Loại`),
Actor chính, Sơ đồ đối chiếu code (commit mà sơ đồ được vẽ lại từ code; thiếu thì ghi "chưa ghi").
  python -X utf8 script/usecase_index.py                 ghi README
  python -X utf8 script/usecase_index.py --check         exit 1 nếu README lệch với các file UC
  python -X utf8 script/usecase_index.py --root ai       danh mục UC của repo con
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START, END = "<!-- uc-index:start -->", "<!-- uc-index:end -->"
TITLE = re.compile(r"^#\s+\S*\s*(UC-\d+):\s*(.+)$", re.M)


def meta(text: str, label: str) -> str:
    m = re.search(rf"^\|\s*\*\*{label}[^*|]*\*\*\s*\|\s*(.+?)\s*\|\s*$", text, re.M)
    return re.sub(r"\s+", " ", m.group(1)).replace("|", "/") if m else "—"


def short(text: str, n: int = 60) -> str:
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"


def table(folder: Path) -> str:
    rows, files = [], []
    for f in folder.glob("UC-*.md"):
        m = re.match(r"UC-(\d+)", f.name)
        if m:
            files.append((int(m.group(1)), f))
        else:
            print(f"usecase-index: bỏ qua {f.name} — tên phải là UC-NNN-slug.md")
    for _, f in sorted(files):
        text = f.read_text(encoding="utf-8")
        t = TITLE.search(text)
        code, name = (t.group(1), t.group(2).strip()) if t else (f.stem[:6], f.stem)
        diagram = meta(text, "Sơ đồ đối chiếu code")
        rows.append(f"| [{code}]({f.name}) | {name.replace('|', '/')} | {meta(text, 'Module')} | "
                    f"{short(meta(text, 'Actor chính'))} | {short(meta(text, 'Trạng thái'))} | "
                    f"{'chưa ghi' if diagram == '—' else short(diagram, 30)} |")
    head = ["| Mã UC | Tên Use-Case | Phân hệ | Actor | Trạng thái | Sơ đồ đối chiếu code |",
            "|---|---|---|---|---|---|"]
    body = rows or ["| *(Chưa có use-case nào)* | | | | | |"]
    return "\n".join([START, "", "> Sinh bởi `python -X utf8 script/usecase_index.py` — không sửa tay bảng này.", "",
                      *head, *body, "", END])


def render(readme: str, folder: Path) -> str:
    if START not in readme or END not in readme:
        raise SystemExit(f"usecase-index: README thiếu dấu {START} … {END}")
    before, rest = readme.split(START, 1)
    return before + table(folder) + rest.split(END, 1)[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT), help="gốc repo (mặc định repo chứa script)")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    folder = Path(args.root) / "docs/projects/usecases"
    readme = folder / "README.md"
    current = readme.read_text(encoding="utf-8")
    text = render(current, folder)
    if args.check:
        if text != current:
            print("usecase-index: README lệch với các file UC — chạy python -X utf8 script/usecase_index.py")
            return 1
        print("usecase-index: README khớp các file UC")
        return 0
    readme.write_text(text, encoding="utf-8", newline="\n")
    print(f"usecase-index: đã ghi {readme.relative_to(Path(args.root)).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
