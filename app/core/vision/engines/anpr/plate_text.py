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


def _trailing_digit_count(text: str, alnum: list[int]) -> int:
    """Xác định số lượng chữ số ở phần đuôi biển số (4 hoặc 5 số).

    - Biển 9 ký tự chữ-số (vd ``59-C1 123.45``, ``51LD-123.45``): luôn có 5 số cuối.
    - Biển 8 ký tự chữ-số: là biển 1 dòng 5 số (``51H-123.45``) nếu có dấu ``-`` ngay
      sau ký tự thứ 3 hoặc dấu ``.`` tách 2 số cuối; ngược lại (vd ``51LD-1234``,
      ``50-N1 6789``) giữ 4 số cuối để không sửa nhầm ký tự sê-ri thứ 4.
    """
    if len(alnum) >= 9:
        return 5
    if len(alnum) == 8:
        between_2_and_3 = text[alnum[2] + 1 : alnum[3]]
        between_5_and_6 = text[alnum[5] + 1 : alnum[6]]
        if "-" in between_2_and_3 or "." in between_5_and_6:
            return 5
    return _TRAILING_DIGITS


def correct_plate_confusions(text: str) -> str:
    """Sửa nhầm chữ↔số theo vị trí của biển dân sự VN, giữ nguyên dấu phân cách.

    Biển dân sự (bỏ dấu) luôn là: 2 số mã tỉnh · 1 chữ sê-ri · … · 4–5 số cuối,
    ví dụ ``51H98888``, ``59C112345``, ``51LD12345``. Chỉ sửa ba vùng chắc chắn đó;
    vị trí giữa (sê-ri thứ hai có thể là chữ hoặc số) để nguyên. Chuỗi không mang
    hình dạng này (biển quân sự ``TM1234``, mảnh đọc sót) trả về y nguyên.
    """
    alnum = [index for index, char in enumerate(text) if char.isalnum()]
    if not _PLAUSIBLE_MIN_LEN <= len(alnum) <= _PLAUSIBLE_MAX_LEN:
        return text
    trailing_digits = _trailing_digit_count(text, alnum)
    chars = list(text)
    for position, index in enumerate(alnum):
        if position < 2 or position >= len(alnum) - trailing_digits:
            chars[index] = chars[index].translate(_LETTER_TO_DIGIT)
        elif position == 2:
            chars[index] = chars[index].translate(_DIGIT_TO_LETTER)
    return "".join(chars)


def format_vietnam_plate(text: str, is_two_line: bool = False) -> str:
    """Định dạng tường minh chuỗi biển số Việt Nam để hiển thị/chuẩn hoá khi cần.

    Không tự gọi trong ``sanitize_plate_text`` để giữ nguyên hợp đồng so khớp chuỗi
    với backend. Hỗ trợ biển 1 dòng 4–5 số (``51F-178.12``, ``51F-1234``) và biển
    2 dòng / sê-ri 2 ký tự (``59-K1 123.45``, ``51LD-123.45``).
    """
    corrected = correct_plate_confusions(sanitize_plate_text(text))
    key = plate_key(corrected)
    if not is_plausible_plate_shape(key):
        return corrected
    if len(key) == 8 and key[:2].isdigit() and key[2].isalpha() and key[3:].isdigit() and not is_two_line:
        return f"{key[:3]}-{key[3:6]}.{key[6:]}"
    if len(key) == 7 and key[:2].isdigit() and key[2].isalpha() and key[3:].isdigit():
        return f"{key[:3]}-{key[3:]}"
    if len(key) == 9 and key[:2].isdigit() and key[2].isalpha() and key[4:].isdigit():
        if is_two_line:
            return f"{key[:2]}-{key[2:4]} {key[4:7]}.{key[7:]}"
        return f"{key[:4]}-{key[4:7]}.{key[7:]}"
    if len(key) == 8 and key[:2].isdigit() and key[2].isalpha() and key[4:].isdigit():
        if is_two_line:
            return f"{key[:2]}-{key[2:4]} {key[4:]}"
        return f"{key[:4]}-{key[4:]}"
    return corrected


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
