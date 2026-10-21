#!/usr/bin/env python3
"""Offline branch/PR record validation. Never executes event metadata as code."""
import argparse
from datetime import date
import json
import os
from pathlib import Path, PurePosixPath
import re

BRANCH = re.compile(r"(?:feature|bugfix|hotfix|chore|docs|codex)/(?P<record>(?:ISSUE|bug|PROB|CHORE)-[0-9]{3})-(?P<month>[0-9]{4}-[0-9]{2})-[a-z0-9]+(?:-[a-z0-9]+)*\Z")
ROOTS = {"ISSUE": "docs/projects/issues", "bug": "docs/projects/bugs", "PROB": "docs/problems",
         "CHORE": "docs/projects/chores"}


def safe_path(value, record):
    """Only Markdown records in the correct namespace; no arbitrary file reads."""
    path = PurePosixPath(value)
    kind = record.rsplit("-", 1)[0]
    if (path.is_absolute() or "\\" in value or ":" in value or ".." in path.parts
            or path.suffix != ".md" or not value.startswith(ROOTS[kind] + "/")
            or any(part.startswith(".") or "-backup-" in part.lower()
                   or part.lower() in {"secretkeys", "thong tin ca nhan"} for part in path.parts)):
        raise ValueError("Policy-Path must be a safe Markdown record path in its namespace")
    parts = path.relative_to(ROOTS[kind]).parts
    if parts and re.fullmatch(r"[0-9]{2}-[0-9]{4}", parts[0]):
        parts = parts[1:]
    flat = len(parts) == 1 and re.fullmatch(re.escape(record) + r"(?:-[a-z0-9]+(?:-[a-z0-9]+)*)?\.md", parts[0])
    canonical_name = {"ISSUE": "issue.md", "bug": "bug.md", "CHORE": "issue.md"}.get(kind)
    folder = (len(parts) == 2 and canonical_name and parts[1] == canonical_name
              and re.fullmatch(re.escape(record) + r"(?:-[a-z0-9]+(?:-[a-z0-9]+)*)?", parts[0]))
    if not (flat or folder):
        raise ValueError("Policy-Path must identify the canonical primary record, never a phase/review child")
    return path


def creation_month(path):
    text = path.read_text(encoding="utf-8-sig")
    # Restrict to creation/report/opening metadata, never modification/resolution dates.
    dates = []
    for line in text.splitlines():
        if line.startswith("|"):
            label = line.split("|")[1].replace("*", "").strip().lower()
            if not re.fullmatch(r"(?:ngày(?: tạo| mở| báo| báo cáo| phát hiện)?(?:\s*/\s*người (?:báo|viết))?|người báo\s*/\s*ngày|created(?: at| date)?|reported(?: at)?|opened(?: at)?)", label):
                continue
            found = re.search(r"\b([0-9]{4}-[0-9]{2}-[0-9]{2})\b", line)
            if found:
                dates.append(date.fromisoformat(found[1]).strftime("%Y-%m"))
    folders = [f"{m[2]}-{m[1]}" for part in path.parts
               if (m := re.fullmatch(r"([0-9]{2})-([0-9]{4})", part))]
    months = set(dates or folders)
    if len(months) != 1:
        raise ValueError("Record creation date is missing or ambiguous; verify its original date")
    month = months.pop()
    date.fromisoformat(month + "-01")
    if folders and any(folder != month for folder in folders):
        raise ValueError("Record creation month conflicts with its month directory")
    return month


def find_records(repo, record):
    base = repo / ROOTS[record.rsplit("-", 1)[0]]
    found = []
    if not base.is_dir() or base.resolve() != base.absolute():
        return found
    for current, dirs, files in os.walk(base, followlinks=False):
        dirs[:] = [d for d in dirs if not d.startswith(".") and "-backup-" not in d.lower()
                   and d.lower() not in {"secretkeys", "thong tin ca nhan"}
                   and not (Path(current) / d).is_symlink()]
        for name in files:
            path = Path(current) / name
            if (path.name.startswith(record + "-") or path.name in {record + ".md", "bug.md", "issue.md"}) and path.suffix == ".md" and not path.is_symlink():
                try:
                    safe_path(path.relative_to(repo).as_posix(), record)
                    found.append(path)
                except ValueError:
                    pass
    return found


def fields(body):
    result = {}
    for key in ("Record", "Path", "Created"):
        matches = re.findall(r"^Policy-" + key + r":\s*(.*?)\s*$", body, re.M)
        if len(matches) != 1:
            raise ValueError("PR body requires exactly one Policy-" + key + " line")
        result[key] = matches[0]
    return result


def validate(repo, config, branch, pr=None):
    # Naming exemptions do not waive ADR-0042's universal PR title traceability.
    if pr is not None and not re.search(r"(?<![A-Za-z0-9-])(?:ISSUE|bug|PROB|CHORE)-[0-9]{3}(?![A-Za-z0-9-])", pr.get("title", "")):
        raise ValueError("Every PR title must reference a record, including exempt branch names")
    if branch in {"main", "develop"} or branch.startswith("dependabot/"):
        return "EXEMPT_NAME: stable/dependency branch; PR title traceability required, full record metadata not verified"
    if branch in config["legacy_branches"]:
        return "LEGACY: exact pre-existing name; PR title traceability required, full record metadata not verified"
    match = BRANCH.fullmatch(branch)
    if not match:
        raise ValueError("Expected <type>/<ISSUE|bug|PROB|CHORE>-NNN-YYYY-MM-english-kebab-slug")
    record, month = match["record"], match["month"]
    # Nhánh chore gom việc vặt theo tháng (ADR-0055): CHORE chỉ đi với type chore/.
    if record.startswith("CHORE-") and not branch.startswith("chore/"):
        raise ValueError("CHORE records only use the chore/ branch type")
    date.fromisoformat(month + "-01")
    if pr is not None:
        if not re.search(r"(?<![A-Za-z0-9-])" + re.escape(record) + r"(?![A-Za-z0-9-])", pr.get("title", "")):
            raise ValueError("PR title must reference the branch's primary record")
        meta = fields(pr.get("body") or "")
        owner_record = meta["Record"].split()
        if len(owner_record) != 2 or owner_record[1] != record:
            raise ValueError("Policy-Record must be '<repository namespace> <branch record>'")
        owner = owner_record[0]
        if owner not in {config["namespace"], "IPLMS"}:
            raise ValueError("Record namespace is neither this repository nor umbrella IPLMS")
        if record.startswith("PROB-") and owner != "IPLMS":
            raise ValueError("PROB records belong to umbrella IPLMS")
        relative = safe_path(meta["Path"], record)
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", meta["Created"]):
            raise ValueError("Policy-Created must use YYYY-MM-DD")
        if date.fromisoformat(meta["Created"]).strftime("%Y-%m") != month:
            raise ValueError("Policy-Created does not match branch month")
        for part in relative.parts:
            folder = re.fullmatch(r"([0-9]{2})-([0-9]{4})", part)
            if folder and f"{folder[2]}-{folder[1]}" != month:
                raise ValueError("Policy-Path month directory conflicts with branch month")
        if owner != config["namespace"]:
            return "EXTERNAL_UNVERIFIED: umbrella path/date declared; reviewer must verify source record in IPLMS"
        path = repo.joinpath(*relative.parts)
        if not path.is_file() or path.resolve() != path.absolute():
            raise ValueError("Local Policy-Path must exist without symlink traversal")
        candidates = [path]
    else:
        candidates = find_records(repo, record)
        if not candidates:
            return "EXTERNAL_PENDING_PR: name/date syntax valid; record missing locally, PR metadata and review required"
    # ISSUE directories may include phase docs: all matching dates must be consistent.
    months = {creation_month(path) for path in candidates}
    if months != {month}:
        raise ValueError("Branch month does not match original record creation month")
    return "VERIFIED_LOCAL: record exists in repository namespace with matching creation month"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branch", help="Local check; otherwise consume GitHub event JSON")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parent.parent
    config = json.loads((repo / "script/branch_policy.json").read_text(encoding="utf-8"))
    pr = None
    branch = args.branch
    if branch is None:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        pr = event.get("pull_request")
        branch = pr["head"]["ref"] if pr else event.get("ref", "").removeprefix("refs/heads/")
    try:
        print(validate(repo, config, branch, pr))
        return 0
    except (ValueError, OSError) as error:
        print("POLICY FAILED:", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
