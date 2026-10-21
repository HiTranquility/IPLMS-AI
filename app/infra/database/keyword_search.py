"""Nhánh keyword của hybrid search: bỏ dấu tiếng Việt và ghép từ khoá bằng OR.

Vì sao không dùng ``websearch_to_tsquery``: nó AND mọi từ, nên câu hỏi tự nhiên
"phí gửi xe là bao nhiêu" chỉ khớp đoạn văn chứa cả "là", "bao", "nhiêu" — gần
như không đoạn nào. Ở đây bỏ hư từ, ghép phần còn lại bằng OR và để
``ts_rank_cd`` xếp đoạn khớp nhiều từ lên trên.

Vì sao bỏ dấu bằng ``translate()`` thay cho extension ``unaccent``: ``translate``
là hàm IMMUTABLE có sẵn, đánh index biểu thức được và không cần quyền tạo
extension trên DB. Biểu thức trong index và trong câu truy vấn phải giống hệt
nhau từng ký tự, nên cả hai đều lấy từ ``FOLDED_CONTENT_TSVECTOR``.
"""
from __future__ import annotations

import re
import unicodedata

_VIETNAMESE_LETTERS = (
    "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
)


def _fold_char(char: str) -> str:
    base = "".join(
        part for part in unicodedata.normalize("NFD", char) if unicodedata.category(part) != "Mn"
    )
    return "d" if char in "đĐ" else base.lower()


_FOLD_SOURCE = "".join(
    sorted(set(_VIETNAMESE_LETTERS + _VIETNAMESE_LETTERS.upper()))
)
_FOLD_TARGET = "".join(_fold_char(char) for char in _FOLD_SOURCE)
_FOLD_TABLE = str.maketrans(_FOLD_SOURCE, _FOLD_TARGET)

FOLDED_CONTENT_TSVECTOR = (
    f"to_tsvector('simple', translate(content, '{_FOLD_SOURCE}', '{_FOLD_TARGET}'))"
)

# Hư từ hay gặp trong câu hỏi; so ở dạng CÓ DẤU vì bỏ dấu xong sẽ trùng từ có
# nghĩa ("thế" → "the" = "thẻ", "đó" → "do" = "đỗ").
_STOPWORDS = frozenset(
    """là bao nhiêu gì có không thì của cho được và các những một tôi mình bạn
    nào sao như thế ở đâu khi nếu với này đó ạ vậy hả nhé hay phải bị sẽ đã đang
    rồi mà lúc""".split()
)


def fold(text: str) -> str:
    """Bỏ dấu + chữ thường, khớp đúng phép ``translate`` phía SQL."""
    return unicodedata.normalize("NFC", text).translate(_FOLD_TABLE).lower()


def build_keyword_tsquery(text: str) -> str | None:
    """Câu hỏi → chuỗi ``to_tsquery`` dạng ``phi | gui | xe``; ``None`` khi rỗng."""
    words = re.findall(r"\w+", unicodedata.normalize("NFC", text).lower())
    meaningful = [word for word in words if word not in _STOPWORDS] or words
    terms = dict.fromkeys(
        term
        for word in meaningful
        for term in re.findall(r"[0-9a-z]+", fold(word))
    )
    return " | ".join(terms) or None
