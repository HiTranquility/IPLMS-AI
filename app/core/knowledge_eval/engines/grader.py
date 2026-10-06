"""Chấm một câu trả lời Copilot so với test case — phần TẤT ĐỊNH.

Số tiền, giờ, nguồn trích dẫn và "phải từ chối" được so bằng quy tắc, không
nhờ LLM: một LLM chấm có thể "khen" câu trả lời nói 35.000đ trong khi quy chế
ghi 25.000đ. LLM-as-judge (xem `judge.py`) chỉ chấm phần diễn giải của câu
`explain`, và chỉ khi phần tất định đã qua.

Module CỐ Ý chỉ dùng stdlib — test được không cần mạng/API key.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional

KINDS = ("fact", "explain", "abstain")

# Dấu hiệu Copilot từ chối vì kho tri thức không có (khớp NO_CONTEXT_ANSWER +
# câu SYSTEM_PROMPT yêu cầu nói rõ khi thiếu ngữ cảnh — rag_pipeline.py).
_REFUSAL_MARKERS = (
    "chua tim thay",
    "khong tim thay",
    "chua co du thong tin",
    "khong co du thong tin",
    "khong co thong tin",
    "kho tri thuc chua co",
    "chua du thong tin",
)


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return stripped.replace("đ", "d").replace("Đ", "D")


def normalize(text: str) -> str:
    """Đưa về một dạng so sánh được: `25.000 VNĐ` == `25000đ`, `22h00` == `22:00`."""
    value = unicodedata.normalize("NFC", text or "").lower()
    # Tiền tệ về một ký hiệu, rồi xoá dấu phân cách hàng nghìn giữa các chữ số.
    value = re.sub(r"\s*(vnđ|vnd|đồng|dong|đ)\b", "đ", value)
    value = re.sub(r"(?<=\d)[.,\s](?=\d{3}(?!\d))", "", value)
    value = re.sub(r"(\d+)\s*k\b", lambda m: m.group(1) + "000", value)
    # Giờ: 22h, 22h00, 22 giờ, 22:00 → 22:00
    value = re.sub(
        r"\b(\d{1,2})\s*(?:h|giờ|:)\s*(\d{2})?\b",
        lambda m: f"{int(m.group(1)):02d}:{m.group(2) or '00'}",
        value,
    )
    value = re.sub(r"\s*đ\b", "đ", value)
    return re.sub(r"\s+", " ", value).strip()


def contains_fact(normalized_answer: str, normalized_fact: str) -> bool:
    """Tìm `fact` trong câu trả lời, KHÔNG cho số dính liền chữ số khác.

    So chuỗi con trần thì đáp án ``25000đ`` "có mặt" trong câu trả lời sai
    ``125000đ`` — đúng loại sai tiền mà cổng xuất bản sinh ra để chặn.
    """
    pattern = re.escape(normalized_fact)
    if normalized_fact[:1].isdigit():
        pattern = r"(?<!\d)" + pattern
    if normalized_fact[-1:].isdigit():
        pattern += r"(?!\d)"
    return re.search(pattern, normalized_answer) is not None


def is_refusal(answer: str) -> bool:
    plain = _strip_accents(normalize(answer))
    return any(marker in plain for marker in _REFUSAL_MARKERS)


@dataclass
class Grade:
    passed: bool
    reasons: List[str] = field(default_factory=list)
    # True khi phần tất định đã qua và câu cần judge chấm tiếp phần diễn giải.
    needs_judge: bool = False


def grade(
    kind: str,
    answer: str,
    sources: List[str],
    expected_facts: List[str],
    expected_source: str = "",
    retrieved_nothing: Optional[bool] = None,
) -> Grade:
    """Chấm tất định. `retrieved_nothing` = truy xuất không ra đoạn nào."""
    abstained = bool(retrieved_nothing) or is_refusal(answer)

    if kind == "abstain":
        if abstained:
            return Grade(True, ["Copilot từ chối đúng vì tài liệu không có thông tin."])
        return Grade(False, ["Câu này phải được từ chối nhưng Copilot vẫn trả lời (nguy cơ bịa)."])

    reasons: List[str] = []
    if abstained:
        reasons.append("Copilot từ chối trả lời dù tài liệu có đáp án.")
    normalized_answer = normalize(answer)
    missing = [
        fact
        for fact in expected_facts
        if normalize(fact) and not contains_fact(normalized_answer, normalize(fact))
    ]
    if missing:
        reasons.append("Thiếu hoặc sai thông tin bắt buộc: " + ", ".join(missing))
    if expected_source and not any(expected_source.lower() in s.lower() for s in sources):
        reasons.append(f"Không trích đúng nguồn mong đợi: {expected_source}")

    if reasons:
        return Grade(False, reasons)
    if kind == "explain":
        return Grade(True, ["Đạt phần kiểm tra tất định."], needs_judge=True)
    return Grade(True, ["Đúng mọi thông tin bắt buộc."])
