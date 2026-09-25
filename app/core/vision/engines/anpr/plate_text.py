"""Luật chuỗi biển số Việt Nam — thuần, không phụ thuộc model."""
import re

from app.core.constants import PLATE_MAX_LENGTH, PLATE_MIN_ALPHA

# Hình dạng thường gặp sau khi bỏ dấu phân cách: 7–10 ký tự, ≥5 chữ số.
_PLAUSIBLE_MIN_LEN = 7
_PLAUSIBLE_MAX_LEN = 10
_PLAUSIBLE_MIN_DIGITS = 5


def sanitize_plate_text(text: str) -> str:
    text = text.upper()
    return re.sub(r"[^A-Z0-9\-.]", "", text)


def is_valid_plate(text: str) -> bool:
    """Kiểm tra biển số hợp lệ: tối đa PLATE_MAX_LENGTH ký tự, ít nhất PLATE_MIN_ALPHA chữ cái."""
    return (
        len(text) <= PLATE_MAX_LENGTH
        and len(re.findall(r"[A-Z]", text)) >= PLATE_MIN_ALPHA
    )


def plate_key(text: str) -> str:
    """Khoá dùng để so kết quả giữa các nhánh OCR.

    Dấu ``-``/``.`` thường biến mất sau resize hoặc threshold. Chúng vẫn được
    giữ trong kết quả trả về, nhưng không nên làm hai lần đọc cùng một biển bị
    xem là hai kết quả khác nhau.
    """
    return re.sub(r"[^A-Z0-9]", "", sanitize_plate_text(text))


def is_plausible_plate_shape(text: str) -> bool:
    """Điểm cộng mềm cho hình dạng thường gặp, không thay validation hiện tại."""
    key = plate_key(text)
    digits = sum(char.isdigit() for char in key)
    letters = sum(char.isalpha() for char in key)
    return (
        _PLAUSIBLE_MIN_LEN <= len(key) <= _PLAUSIBLE_MAX_LEN
        and digits >= _PLAUSIBLE_MIN_DIGITS
        and letters >= PLATE_MIN_ALPHA
    )


def separator_evidence(text: str) -> int:
    """Số dấu phân cách OCR thật sự nhìn thấy, không tự suy diễn/chèn thêm."""
    return int("-" in text) + int("." in text)
