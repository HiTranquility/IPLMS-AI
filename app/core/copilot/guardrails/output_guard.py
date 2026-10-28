"""Chặn câu trả lời khẳng định điều tài liệu không hề có (PROB-046).

Prompt không chặn được prompt injection: A/B trên qwen2.5:3b, câu hỏi tự chèn
"ngữ cảnh" giả vẫn thắng 18–20/20 ở mọi cách dựng prompt. Vì vậy kiểm đầu ra
bằng luật tất định, đối chiếu với đúng các đoạn đã truy xuất — KHÔNG đối chiếu
với câu hỏi, vì câu hỏi là thứ kẻ tấn công viết.

Chỉ bắt những thứ gây hại thật nếu sai: báo "miễn phí", đưa link, đưa số điện
thoại/tài khoản. Số tiền tính ra (25.000đ × 3 = 75.000đ) không bị chặn.
"""
from __future__ import annotations

import re
from typing import AsyncGenerator, AsyncIterable

from app.core.copilot.messages import GUARD_NOTICE

_FREE = re.compile(
    r"(?:m[\s._-]*i[\s._-]*ễ[\s._-]*n|m[\s._-]*i[\s._-]*e[\s._-]*n)[\s._-]*(?:p[\s._-]*h[\s._-]*í|p[\s._-]*h[\s._-]*i)"
    r"|\b0\s*(?:đ|đồng|vnđ|vnd)\b"
    r"|miễn\s*phí"
    r"|không\s*thu\s*phí",
    re.IGNORECASE,
)
_URL = re.compile(
    r"(?:https?://|www\.)\S+|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|net|org|vn|me|ly|io|xyz|info|top|link)\b(?:/\S*)?",
    re.IGNORECASE,
)
# Dãy số (cho phép một dấu cách/chấm/gạch giữa các chữ số); ≥ 9 chữ số mà không
# phải số tiền thì coi là SĐT/số tài khoản.
_NUMBER_RUN = re.compile(r"\d(?:[ .-]?\d)*")
_MONEY_SUFFIX = re.compile(r"\s*(?:đ|đồng|vnđ|vnd)\b", re.IGNORECASE)
# Giữ lại cuối luồng đủ dài để chưa phát ra một mẫu đang viết dở.
_HOLD_CHARS = 40


def violation(answer: str, context: str) -> str | None:
    """Tên luật bị vi phạm, hoặc None. Chỉ nhìn ngữ cảnh đã truy xuất."""
    ctx = context.casefold()
    if _FREE.search(answer) and not _FREE.search(context):
        return "free_claim"
    for match in _URL.finditer(answer):
        if match.group(0).rstrip(".,;:)]").casefold() not in ctx:
            return "unknown_link"
    ctx_digits = {re.sub(r"\D", "", m.group(0)) for m in _NUMBER_RUN.finditer(context)}
    for match in _NUMBER_RUN.finditer(answer):
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) < 9 or _MONEY_SUFFIX.match(answer, match.end()):
            continue
        if digits not in ctx_digits:
            return "unknown_number"
    return None


async def guard_stream(
    tokens: AsyncIterable[str], context: str, on_violation
) -> AsyncGenerator[str, None]:
    """Phát token nhưng giữ lại đuôi chưa chắc an toàn; vi phạm thì dừng và báo.

    Chỉ nhả tới khoảng trắng cuối cùng trước vùng giữ, để link/số dài chưa viết
    xong không lọt ra từng nửa.
    """
    text = ""
    released = 0
    async for token in tokens:
        text += token
        # Chỉ kiểm phần đã viết xong (tới khoảng trắng cuối): "0901 234 56" đang
        # viết dở của một số có trong tài liệu không được tính là số lạ.
        rule = violation(text[: text.rfind(" ") + 1], context)
        if rule:
            on_violation(rule)
            yield ("\n\n" if released else "") + GUARD_NOTICE
            return
        cut = text.rfind(" ", released, max(released, len(text) - _HOLD_CHARS))
        if cut > released:
            yield text[released:cut]
            released = cut
    rule = violation(text, context)
    if rule:
        on_violation(rule)
        yield ("\n\n" if released else "") + GUARD_NOTICE
    elif released < len(text):
        yield text[released:]
