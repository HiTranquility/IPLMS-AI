"""Che dữ liệu cá nhân trong câu hỏi/câu trả lời trước khi lưu telemetry (ADR-0049).

Che thô bằng mẫu: thà che nhầm một chuỗi số vô hại còn hơn lưu lộ biển số hay
số điện thoại. Không dùng để quyết định nghiệp vụ.
"""
import re

_PATTERNS = (
    ("[EMAIL]", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    # Biển số VN: 51H-123.45, 59C 888.66, 30A12345, 29-B1 123.45
    ("[BIEN_SO]", re.compile(
        r"\b\d{2}\s?-?\s?[A-Z]{1,2}\d?\s?-?\s?\d{3}\.?\d{1,2}\b", re.IGNORECASE)),
    ("[SDT]", re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.-]?\d){9,10}(?!\d)")),
    ("[SO]", re.compile(r"(?<!\d)\d{9,}(?!\d)")),
)


def redact(text: str) -> str:
    for label, pattern in _PATTERNS:
        text = pattern.sub(label, text)
    return text
