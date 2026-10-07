"""Cổng xuất bản (SUGGESTION-009 R3/R4) — logic thuần, không I/O.

Đã chốt 2026-09-25: KHÔNG có đường bỏ qua (kể cả admin).
"""
import hashlib
from typing import Any, Dict, Iterable, List, Optional, Tuple


def fingerprint(items: Iterable[str]) -> str:
    """Dấu vân tay ổn định của một tập (thứ tự không quan trọng)."""
    return hashlib.sha256("\n".join(sorted(items)).encode("utf-8")).hexdigest()


def suite_fingerprint(cases: Iterable[Dict[str, Any]]) -> str:
    # id + thời điểm sửa: thêm/xoá/sửa bất kỳ case nào đều đổi vân tay.
    return fingerprint(f"{case['id']}@{case['updated_at']}" for case in cases)


def run_verdict(
    total: int,
    passed: int,
    failed_facts: int,
    failed_abstain: int,
    min_cases: int,
    min_pass_ratio: float,
) -> Tuple[bool, List[str]]:
    """Một lượt chạy xong có ĐẠT ngưỡng R4 không, kèm lý do khi trượt."""
    reasons: List[str] = []
    if total < min_cases:
        reasons.append(f"Bộ test cần tối thiểu {min_cases} câu (hiện {total}).")
    ratio = passed / total if total else 0.0
    if ratio < min_pass_ratio:
        reasons.append(f"Tỉ lệ đúng {ratio:.0%} thấp hơn ngưỡng {min_pass_ratio:.0%}.")
    if failed_facts:
        reasons.append(f"{failed_facts} câu sai về số liệu (tiền/giờ) — phải bằng 0.")
    if failed_abstain:
        reasons.append(f"{failed_abstain} câu đáng lẽ phải từ chối nhưng Copilot vẫn trả lời.")
    return not reasons, reasons


def injection_reasons(flagged: Iterable[Tuple[str, int, str]]) -> List[str]:
    """Tài liệu có đoạn giống lệnh cho AI thì chặn (PROB-046, ADR-0029) — không có đường bỏ qua."""
    return [
        f"Tài liệu {source}: {count} đoạn giống lệnh gửi cho trợ lý AI (vd “{sample}”) — "
        "xoá chỗ đó rồi nạp lại."
        for source, count, sample in flagged
    ]


def readiness(
    latest_run: Optional[Dict[str, Any]],
    current_docs_fingerprint: str,
    current_suite_fingerprint: str,
    unpublished_in_run: int,
) -> List[str]:
    """Lý do CHƯA được xuất bản; danh sách rỗng = được xuất bản."""
    if latest_run is None:
        return ["Chưa chạy test lần nào cho phạm vi này."]
    status = latest_run["status"]
    if status == "RUNNING":
        return ["Lượt chạy test đang chạy — đợi xong rồi xuất bản."]
    reasons: List[str] = []
    if status != "PASSED":
        reasons.append("Lượt chạy gần nhất chưa đạt ngưỡng.")
        reasons.extend(latest_run.get("verdict_reasons") or [])
        if latest_run.get("error"):
            reasons.append(latest_run["error"])
    if latest_run["docs_fingerprint"] != current_docs_fingerprint:
        reasons.append("Tài liệu đã thay đổi sau lượt chạy gần nhất — chạy lại test.")
    if latest_run["suite_fingerprint"] != current_suite_fingerprint:
        reasons.append("Bộ test đã thay đổi sau lượt chạy gần nhất — chạy lại test.")
    if not reasons and unpublished_in_run == 0:
        reasons.append("Không có bản nháp mới nào để xuất bản.")
    return reasons
