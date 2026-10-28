"""Chuẩn hoá chuỗi trước khi so regex guard (bug-049).

Guard so regex trên chuỗi thô thì bị lách bằng thứ người đọc không thấy khác:
ký tự rộng 0 chen giữa chữ, chữ Cyrillic/Greek trông như Latin, chữ full-width,
hoặc tách từng chữ bằng khoảng trắng ("h t t p s : / / …"). Chuỗi chuẩn hoá chỉ
dùng để so khớp; nội dung phát ra người dùng vẫn là bản gốc.
"""
from __future__ import annotations

import re
import unicodedata

# Ký tự người đọc không thấy: mọi ký tự định dạng (category Cf — rộng 0, gạch nối mềm,
# điều khiển hướng chữ, tag U+E0000…) cộng nhóm Default_Ignorable không thuộc Cf.
_IGNORABLE_EXTRA = re.compile("[\u034f\u115f\u1160\u17b4\u17b5\u180b-\u180f\u3164\ufe00-\ufe0f\uffa0\U000e0100-\U000e01ef]")
_CONFUSABLES = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "i", "ј": "j", "ѕ": "s",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T",
    "Х": "X", "У": "Y", "І": "I", "Ј": "J", "Ѕ": "S",
    "ο": "o", "α": "a", "ε": "e", "ι": "i", "ρ": "p", "τ": "t", "υ": "u", "ν": "v",
    "Ο": "O", "Α": "A", "Ε": "E", "Ι": "I", "Ρ": "P", "Τ": "T", "Κ": "K", "Μ": "M", "Ν": "N",
})
# ≥ 4 ký tự đơn cách nhau đúng một khoảng trắng: chữ bị tách để lách regex.
_SPACED_RUN = re.compile(r"(?<!\S)\S(?: \S){3,}(?!\S)")


def _drop_invisible(text: str, replacement: str) -> str:
    text = "".join(replacement if unicodedata.category(ch) == "Cf" else ch for ch in text)
    return _IGNORABLE_EXTRA.sub(replacement, text)


def normalize_for_match(text: str, invisible_as: str = "") -> str:
    """Bản để so khớp. ``invisible_as=" "`` cho luật cần ranh giới từ: ký tự ẩn dùng thay
    dấu cách ("bỏ\u200bqua\u200bquy\u200btắc") phải thành khoảng trắng, không phải dính chữ."""
    # Bỏ ký tự ẩn trước NFKC: chen giữa chữ gốc và dấu kết hợp thì NFKC không ghép được.
    text = unicodedata.normalize("NFKC", _drop_invisible(text, invisible_as)).translate(_CONFUSABLES)
    return _SPACED_RUN.sub(lambda m: m.group(0).replace(" ", ""), text)
