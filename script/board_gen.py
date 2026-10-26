#!/usr/bin/env python3
"""Sinh docs/projects/BOARD.md từ Meta hồ sơ của chính repo (IPLMS ADR-0060).

Bản giống hệt ở gốc IPLMS và 6 repo con; chỉ dùng stdlib, chạy được khi repo con clone riêng.
Nguồn dòng bảng: bug, ISSUE, CHORE, SUGGESTION trong docs/projects/. Mỗi hồ sơ một dòng, trừ khi
hồ sơ có mục "## 📋 Việc trên BOARD" (mỗi dòng bảng đó thành một dòng BOARD).
Meta đọc: Trạng thái/Status, Người nhận, Hạn, Ưu tiên, Ngày đóng. Kết quả chỉ phụ thuộc nội dung
repo (không ngày chạy, không nhánh) nên hai lần chạy cho cùng byte.

  python -X utf8 script/board_gen.py            ghi docs/projects/BOARD.md (chỉ CI trên develop)
  python -X utf8 script/board_gen.py --stdout   in ra để xem ở local, không ghi
  python -X utf8 script/board_gen.py --check    exit 1 nếu BOARD.md khác bản sinh ra
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJ = ROOT / "docs" / "projects"
OUT = PROJ / "BOARD.md"
DOCS = ROOT / "docs"
# Luôn lên bảng: hồ sơ việc. Loại khác (PROB, IDEA, AUDIT, REQ) chỉ lên khi tự ghi Người nhận hoặc có bảng việc.
GLOBS = ("projects/bugs/bug-*.md", "projects/bugs/*/bug.md", "projects/bugs/*/*/bug.md", "projects/issues/*/*/issue.md",
         "projects/chores/*/*/issue.md", "projects/suggestions/**/SUGGESTION-*.md")
OPT_IN = ("problems/**/PROB-*.md", "ideas/**/IDEA-*.md", "requirements/**/REQ-*.md", "projects/audits/**/AUDIT-*.md")
CODE = re.compile(r"^((?:bug|ISSUE|CHORE|SUGGESTION|PROB|IDEA|REQ|AUDIT)-\d+)")
META = re.compile(r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(.*?)\s*\|\s*$", re.M)
TITLE = re.compile(r"^#\s+(.+)$", re.M)
TASKS = re.compile(r"^##\s+📋\s+Việc trên BOARD\s*$(.*?)(?=^##\s|\Z)", re.M | re.S)
DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
# Luật "xong" của check_drift.is_done (test_board_gen.py so hai hàm), chép lại vì repo con không có check_drift.py;
# riêng bảng thêm: đầu dòng ✅ là xong (trừ khi còn chờ PR/merge), phần "còn …" phía sau là việc của hồ sơ khác.
DONE = re.compile(r"✅|\bDone\b|\bFixed\b|Đã sửa|\bĐóng\b|\bClosed\b|Resolved|Won.t fix|⛔|Cancel|Superseded"
                  r"|Rejected|Từ chối|🗃️|\bAccepted\b", re.I)
RESIDUAL = re.compile(r"còn|chưa|cần|vẫn|pending|remain|\btrừ\b|blocked|chờ", re.I)
OPEN_LEAD = re.compile(r"^\s*(?:🚧|🏗|🧪|📝|🆕)")
BLOCKED = re.compile(r"Bị chặn|\bBlocked\b", re.I)
LEAD = {"🚧": "🚧", "🏗": "🚧", "🧪": "🚧", "🛠": "🚧", "🔧": "🚧", "👀": "⏳", "🔄": "⏳", "⏳": "⏳"}
REVIEW = re.compile(r"\bReview|REVIEWING|chờ duyệt|chờ merge|chưa merge|chờ PR|chờ techlead", re.I)
PROGRESS = re.compile(r"In Progress|Fixing|Đang", re.I)
PRIORITY = {"🔴": 0, "🟠": 1, "🟡": 2, "🟢": 3}
DONE_LIMIT = 20
SECTIONS = [
    ("🙋", "Cần người nhận", ["Việc", "Hồ sơ", "Ưu tiên", "Trạng thái"]),
    ("🗓️", "Đã giao, chưa bắt đầu", ["Việc", "Hồ sơ", "Người nhận", "Hạn", "Ưu tiên"]),
    ("🚧", "Đang làm", ["Việc", "Hồ sơ", "Người nhận", "Hạn", "Tới đâu"]),
    ("⏳", "Chờ duyệt", ["Việc", "Hồ sơ", "Người nhận", "Tới đâu"]),
    ("⛔", "Bị chặn", ["Việc", "Hồ sơ", "Người nhận", "Tới đâu"]),
    ("✅", f"Xong gần đây ({DONE_LIMIT} hồ sơ có Ngày đóng mới nhất)", ["Việc", "Hồ sơ", "Ngày đóng"]),
]
FIELD = {"Việc": "title", "Ưu tiên": "priority", "Trạng thái": "status", "Người nhận": "owner", "Hạn": "due",
         "Tới đâu": "status", "Ngày đóng": "closed"}


def is_done(status: str) -> bool:
    return not OPEN_LEAD.match(status) and bool(DONE.search(status)) and not RESIDUAL.search(status)


def board_done(status: str) -> bool:
    """Đầu dòng ✅ là xong, trừ khi còn chờ PR/merge (vẫn phải hiện ở ⏳)."""
    return (status.lstrip().startswith("✅") and not REVIEW.search(status)) or is_done(status)


def section_of(status: str, owner: str) -> str:
    if BLOCKED.search(status):
        return "⛔"
    if board_done(status):
        return "✅"
    lead = status.strip()[:2]
    for emoji, sec in LEAD.items():
        if lead.startswith(emoji):
            return sec
    if REVIEW.search(status):
        return "⏳"
    if PROGRESS.search(status):
        return "🚧"
    return "🗓️" if owner else "🙋"


def cell(text: str, limit: int = 0) -> str:
    text = re.sub(r"\s+", " ", text.replace("|", "/")).strip()
    if text in ("—", "-") or text.startswith(("@username", "YYYY")):  # chỗ trống của mẫu
        return ""
    return text[: limit - 1] + "…" if limit and len(text) > limit else text


def table_rows(block: str) -> list[dict[str, str]]:
    lines = []
    for l in block.splitlines():  # chỉ bảng liền mạch đầu tiên; bảng khác trong cùng mục không phải việc
        if l.strip().startswith("|"):
            lines.append(l.strip())
        elif lines:
            break
    if len(lines) < 2:
        return []
    head = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        row = dict(zip(head, cells + [""] * (len(head) - len(cells))))
        if any(row.values()):
            rows.append(row)
    return rows


def record_files() -> list[tuple[Path, bool]]:
    """(file, opt_in) — opt_in: chỉ lên bảng khi hồ sơ tự ghi Người nhận hoặc có bảng việc."""
    found = {p: False for g in GLOBS for p in DOCS.glob(g)}
    found.update({p: True for g in OPT_IN for p in DOCS.glob(g) if p not in found})
    return sorted(((p, o) for p, o in found.items() if not {"templates", "legacy"} & set(p.parts)),
                  key=lambda x: x[0].relative_to(DOCS).as_posix())


def records():
    for f, opt_in in record_files():
        text = f.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
        if text.lstrip().startswith("# ↪️"):  # hồ sơ đã dời (ADR-0054), không phải hồ sơ
            continue
        code = CODE.match(f.parent.name if f.name in ("bug.md", "issue.md") else f.name)
        if not code:
            continue
        meta = {k.strip(): v for k, v in META.findall(meta_text(text))}
        status = next((v for k, v in meta.items() if k.startswith(("Trạng thái", "Status"))), "")
        title = TITLE.search(text)
        title = re.sub(r"^\W*" + re.escape(code.group(1)) + r":\s*(?:\[[^\]]*\]\s*)?", "", title.group(1)) if title else code.group(1)
        base = {"code": code.group(1), "path": Path(os.path.relpath(f, PROJ)).as_posix(), "title": title,
                "owner": meta.get("Người nhận", ""), "due": meta.get("Hạn", ""), "priority": meta.get("Ưu tiên", ""),
                "closed": meta.get("Ngày đóng", ""), "status": status}
        tasks = TASKS.search(text)
        if opt_in and not (tasks or cell(base["owner"])):
            continue
        if not status:
            print(f"board_gen: {base['path']} không có dòng Trạng thái", file=sys.stderr)
        if not tasks:
            yield base
            continue
        for row in table_rows(tasks.group(1)):
            own = row.get("Trạng thái", "") or status
            if board_done(status) and not board_done(own):
                own = status  # hồ sơ đã đóng thì mọi việc con đóng theo
            yield {**base, "title": row.get("Việc", "") or title, "owner": row.get("Người nhận", ""),
                   "due": row.get("Hạn", ""), "priority": row.get("Ưu tiên", "") or base["priority"],
                   "closed": row.get("Ngày đóng", "") or base["closed"], "status": own}


def meta_text(text: str) -> str:
    """Bảng Meta: phần trước mục ## đầu tiên (mẫu bug, suggestion) cộng mục ## 📌 Meta (mẫu issue)."""
    m = re.search(r"^##\s+\S*\s*Meta\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return text.split("\n## ", 1)[0] + "\n" + (m.group(1) if m else "")


def sort_key(r: dict[str, str]) -> tuple:
    prio = next((v for k, v in PRIORITY.items() if k in r["priority"]), 9)
    due = DATE.search(r["due"])
    return (prio, due.group(1) if due else "9999", r["code"], r["title"])


def heading() -> str:
    if OUT.exists():
        first = OUT.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n", 1)[0]
        if first.startswith("# "):
            return first
    return f"# 📋 BOARD — {ROOT.name}: việc chưa làm, ai nhận, tới đâu"


def overview() -> list[str]:
    gm = ROOT / ".gitmodules"
    subs = re.findall(r"^\s*path\s*=\s*(\S+)", gm.read_text(encoding="utf-8"), re.M) if gm.exists() else []
    if not subs:
        return []
    lines = ["## 🗺️ Toàn cảnh — BOARD từng repo con", "", "| Repo con | BOARD |", "|---|---|"]
    lines += [f"| `{s}` | [{s}/docs/projects/BOARD.md](../../{s}/docs/projects/BOARD.md) |" for s in subs]
    return lines + [""]


def render() -> str:
    rows = list(records())
    by = {sec: [] for sec, _, _ in SECTIONS}
    for r in rows:
        by[section_of(r["status"], cell(r["owner"]))].append(r)
    by["✅"] = sorted((r for r in by["✅"] if DATE.search(r["closed"])),
                     key=lambda r: (DATE.search(r["closed"]).group(1), r["code"]), reverse=True)[:DONE_LIMIT]
    lines = [heading(), "",
             "> **Sinh tự động** bởi `python -X utf8 script/board_gen.py` từ Meta hồ sơ — **[NEVER] sửa tay** "
             "(IPLMS ADR-0060). Đổi trạng thái, người nhận, hạn, ưu tiên: sửa Meta của hồ sơ (`Trạng thái`, "
             "`Người nhận`, `Hạn`, `Ưu tiên`, `Ngày đóng`) hoặc bảng `## 📋 Việc trên BOARD` trong hồ sơ. CI sinh lại "
             "bảng sau mỗi lần merge vào `develop`; xem trước ở máy: `python -X utf8 script/board_gen.py --stdout`.",
             "> Ưu tiên: 🔴 hỏng luồng chính / bảo mật / mất dữ liệu · 🟠 sai nhưng có đường vòng, hoặc kiểm thử còn treo "
             "· 🟡 nên làm · 🟢 dọn dẹp, vận hành nhỏ.", ""]
    lines += overview()
    for sec, name, cols in SECTIONS:
        sel = by[sec] if sec == "✅" else sorted(by[sec], key=sort_key)
        lines += [f"## {sec} {name}", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for r in sel:
            vals = []
            for c in cols:
                if c == "Hồ sơ":
                    vals.append(f"[{r['code']}]({r['path']})")
                else:
                    vals.append(cell(r[FIELD[c]], 100 if c in ("Tới đâu", "Trạng thái", "Việc") else 0))
            lines.append("| " + " | ".join(vals) + " |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    text = render()
    if "--stdout" in sys.argv:
        print(text, end="")
        return 0
    if "--check" in sys.argv:
        current = OUT.read_text(encoding="utf-8").replace("\r\n", "\n") if OUT.exists() else ""
        if current != text:
            print("BOARD.md lệch với hồ sơ: CI trên develop sẽ sinh lại; ở local xem bằng --stdout, không commit")
            return 1
        print("BOARD.md khớp hồ sơ")
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"đã ghi {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
