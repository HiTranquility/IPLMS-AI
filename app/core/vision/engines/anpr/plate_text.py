"""Luật chuỗi biển số Việt Nam — thuần, không phụ thuộc model."""
import re

from app.core.constants import PLATE_MAX_LENGTH, PLATE_MIN_ALNUM, PLATE_MIN_ALPHA

# Hình dạng thường gặp sau khi bỏ dấu phân cách: 7–10 ký tự, ≥5 chữ số.
_PLAUSIBLE_MIN_LEN = 7
_PLAUSIBLE_MAX_LEN = 10
_PLAUSIBLE_MIN_DIGITS = 5


def sanitize_plate_text(text: str) -> str:
    text = text.upper()
    return re.sub(r"[^A-Z0-9\-.]", "", text)


# Ký tự OCR hay nhầm, chỉ sửa ở vị trí mà cấu trúc biển VN đã định sẵn loại.
_LETTER_TO_DIGIT = str.maketrans({"O": "0", "D": "0", "Q": "0", "I": "1", "L": "1",
                                  "Z": "2", "S": "5", "G": "6", "B": "8", "T": "7"})
_DIGIT_TO_LETTER = str.maketrans({"0": "D", "8": "B", "5": "S", "2": "Z", "6": "G", "4": "A"})
_TRAILING_DIGITS = 4


def correct_plate_confusions(text: str) -> str:
    """Sửa nhầm chữ↔số theo vị trí của biển dân sự VN, giữ nguyên dấu phân cách.

    Biển dân sự (bỏ dấu) luôn là: 2 số mã tỉnh · 1 chữ sê-ri · … · ≥4 số cuối,
    ví dụ ``51H98888``, ``59C112345``, ``51LD12345``. Chỉ sửa ba vùng chắc chắn đó;
    vị trí giữa (sê-ri thứ hai có thể là chữ hoặc số) để nguyên. Chuỗi không mang
    hình dạng này (biển quân sự ``TM1234``, mảnh đọc sót) trả về y nguyên.
    """
    alnum = [index for index, char in enumerate(text) if char.isalnum()]
    if not _PLAUSIBLE_MIN_LEN <= len(alnum) <= _PLAUSIBLE_MAX_LEN:
        return text
    chars = list(text)
    for position, index in enumerate(alnum):
        if position < 2 or position >= len(alnum) - _TRAILING_DIGITS:
            chars[index] = chars[index].translate(_LETTER_TO_DIGIT)
        elif position == 2:
            chars[index] = chars[index].translate(_DIGIT_TO_LETTER)
    return "".join(chars)


def is_valid_plate(text: str) -> bool:
    """Biển hợp lệ: tối đa PLATE_MAX_LENGTH ký tự, ≥PLATE_MIN_ALNUM chữ/số, ≥PLATE_MIN_ALPHA chữ cái."""
    return (
        len(text) <= PLATE_MAX_LENGTH
        and len(re.findall(r"[A-Z0-9]", text)) >= PLATE_MIN_ALNUM
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
        # Mã tỉnh 11–99: "00", "05" là dấu hiệu đọc sai đầu biển.
        and key[:2].isdigit()
        and 11 <= int(key[:2]) <= 99
    )


def separator_evidence(text: str) -> int:
    """Số dấu phân cách OCR thật sự nhìn thấy, không tự suy diễn/chèn thêm."""
    return int("-" in text) + int("." in text)
