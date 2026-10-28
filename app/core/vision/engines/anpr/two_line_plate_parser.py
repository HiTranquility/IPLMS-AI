"""Bộ phân tích và chuẩn hóa biển số 2 dòng xe máy Việt Nam (ANPR Two-Line Plate Parser).

Theo quy chuẩn Bộ Công An / Cục CSGT (Thông tư 24/2023/TT-BCA):
- Biển số xe mô tô/xe máy gồm 2 dòng:
  + Dòng trên: Ký hiệu địa phương đăng ký xe (mã tỉnh 2 chữ số từ 11 đến 99)
    và sê-ri đăng ký (1 chữ cái + 1 chữ số cho xe >= 50cc, ví dụ '59-K1', '29-B1', '43-C1';
    hoặc 2 chữ cái cho xe < 50cc / xe điện, ví dụ '59-AA', '29-MD').
  + Dòng dưới: Nhóm số thứ tự đăng ký gồm 5 chữ số (hoặc 4 chữ số), ví dụ '123.45', '6789'.
- Biển số ô tô thông thường là 1 dòng dài (ví dụ '51A-123.45', '30F-999.99').
"""
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union


# Bảng sửa nhầm ký tự chữ <-> số cho cấu trúc biển số Việt Nam
_LETTER_TO_DIGIT = str.maketrans({
    "O": "0", "D": "0", "Q": "0",
    "I": "1", "L": "1",
    "Z": "2",
    "S": "5",
    "G": "6",
    "B": "8",
    "T": "7",
    "A": "4",
})

_DIGIT_TO_LETTER = str.maketrans({
    "0": "D",
    "8": "B",
    "5": "S",
    "2": "Z",
    "6": "G",
    "4": "A",
    "1": "I",
    "7": "T",
})


@dataclass
class _BoxItem:
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    text: str
    confidence: float
    has_coords: bool = True

    @property
    def x_center(self) -> float:
        return (self.x_min + self.x_max) / 2.0

    @property
    def y_center(self) -> float:
        return (self.y_min + self.y_max) / 2.0

    @property
    def height(self) -> float:
        return max(1.0, self.y_max - self.y_min)

    @property
    def width(self) -> float:
        return max(1.0, self.x_max - self.x_min)


def _extract_box(item: Any) -> Optional[_BoxItem]:
    """Trích xuất tọa độ bbox, text, và confidence từ item dạng dict hoặc tuple/list."""
    if item is None:
        return None

    # Trường hợp item là dict
    if isinstance(item, dict):
        text = str(item.get("text", "")).strip()
        conf = float(item.get("confidence", item.get("conf", 1.0)))
        
        # Thử lấy tọa độ từ bbox / box / coords
        bbox = item.get("bbox", item.get("box", item.get("coords", None)))
        if bbox is not None:
            return _box_from_raw_bbox(bbox, text, conf)
        
        if all(k in item for k in ("x1", "y1", "x2", "y2")):
            return _BoxItem(
                float(item["x1"]), float(item["y1"]),
                float(item["x2"]), float(item["y2"]),
                text, conf, has_coords=True
            )
        if all(k in item for k in ("xmin", "ymin", "xmax", "ymax")):
            return _BoxItem(
                float(item["xmin"]), float(item["ymin"]),
                float(item["xmax"]), float(item["ymax"]),
                text, conf, has_coords=True
            )
        return _BoxItem(0.0, 0.0, 0.0, 0.0, text, conf, has_coords=False)

    # Trường hợp item là tuple hoặc list
    if isinstance(item, (list, tuple)):
        if len(item) == 0:
            return None
        # Format EasyOCR chuẩn: (bbox, text, conf)
        if len(item) >= 3:
            raw_bbox, text, conf = item[0], str(item[1]).strip(), float(item[2])
            return _box_from_raw_bbox(raw_bbox, text, conf)
        # Format (bbox, text)
        if len(item) == 2:
            raw_bbox, text = item[0], str(item[1]).strip()
            return _box_from_raw_bbox(raw_bbox, text, 1.0)
        # Format chỉ có text
        if len(item) == 1:
            return _BoxItem(0.0, 0.0, 0.0, 0.0, str(item[0]).strip(), 1.0, has_coords=False)

    # Trường hợp item là string
    if isinstance(item, str):
        return _BoxItem(0.0, 0.0, 0.0, 0.0, item.strip(), 1.0, has_coords=False)

    return None


def _box_from_raw_bbox(raw_bbox: Any, text: str, conf: float) -> _BoxItem:
    """Xử lý các dạng tọa độ bbox: polygon 4 điểm [[x,y],...] hoặc [x1, y1, x2, y2]."""
    if not raw_bbox or not isinstance(raw_bbox, (list, tuple)):
        return _BoxItem(0.0, 0.0, 0.0, 0.0, text, conf, has_coords=False)

    # Bbox là danh sách 4 điểm polygon [[x0,y0], [x1,y1], [x2,y2], [x3,y3]]
    if len(raw_bbox) == 4 and isinstance(raw_bbox[0], (list, tuple)):
        try:
            xs = [float(p[0]) for p in raw_bbox]
            ys = [float(p[1]) for p in raw_bbox]
            return _BoxItem(min(xs), min(ys), max(xs), max(ys), text, conf, has_coords=True)
        except (ValueError, IndexError):
            pass

    # Bbox là 4 số [x1, y1, x2, y2]
    if len(raw_bbox) == 4 and all(isinstance(v, (int, float)) for v in raw_bbox):
        return _BoxItem(
            float(raw_bbox[0]), float(raw_bbox[1]),
            float(raw_bbox[2]), float(raw_bbox[3]),
            text, conf, has_coords=True
        )

    return _BoxItem(0.0, 0.0, 0.0, 0.0, text, conf, has_coords=False)


def clean_plate_string(text: str) -> str:
    """Lọc bỏ các ký tự ngoài bảng chữ cái A-Z, số 0-9, dấu gạch ngang và dấu chấm."""
    return re.sub(r"[^A-Z0-9\-.]", "", text.upper())


def normalize_top_line(text: str) -> Tuple[str, str, str]:
    """Chuẩn hóa dòng trên của biển số xe máy Việt Nam (mã tỉnh + sê-ri).

    Returns:
        Tuple (normalized_top, province_code, series)
        Ví dụ: "59-K1" -> ("59-K1", "59", "K1")
    """
    clean = re.sub(r"[^A-Z0-9]", "", text.upper())
    if len(clean) < 3:
        return text.strip(), "", ""

    # 2 ký tự đầu luôn là mã tỉnh (11-99), sửa nhầm chữ sang số
    prov_raw = clean[:2]
    prov = prov_raw.translate(_LETTER_TO_DIGIT)

    # Phần còn lại là sê-ri đăng ký (ví dụ: K1, B1, AA, MD, C1)
    seri_raw = clean[2:]
    seri_chars = list(seri_raw)

    # Ký tự đầu của sê-ri phải là chữ cái
    if seri_chars and seri_chars[0].isdigit():
        seri_chars[0] = seri_chars[0].translate(_DIGIT_TO_LETTER)

    # Ký tự thứ hai của sê-ri nếu có thể là số (xe >= 50cc) hoặc chữ (xe < 50cc / điện)
    # Giữ nguyên bản chất alphanumeric
    seri = "".join(seri_chars)

    normalized = f"{prov}-{seri}" if seri else prov
    return normalized, prov, seri


def normalize_bottom_line(text: str) -> Tuple[str, str]:
    """Chuẩn hóa dòng dưới của biển số xe máy Việt Nam (nhóm 4 hoặc 5 số).

    Returns:
        Tuple (display_bottom, digits_only)
        Ví dụ: "123.45" -> ("123.45", "12345")
               "6789"   -> ("6789", "6789")
    """
    clean = re.sub(r"[^A-Z0-9.]", "", text.upper())
    # Toàn bộ ký tự chữ cái ở dòng dưới đều do OCR đọc nhầm từ chữ số
    digits_converted = "".join(c.translate(_LETTER_TO_DIGIT) if c.isalnum() else c for c in clean)
    digits = re.sub(r"[^0-9]", "", digits_converted)

    # Định dạng hiển thị chuẩn có dấu chấm:
    # 5 số: 123.45
    # 4 số: 6789 hoặc 67.89
    if len(digits) == 5:
        display = f"{digits[:3]}.{digits[3:]}"
    elif len(digits) == 4 and "." in clean:
        parts = clean.split(".")
        if len(parts) == 2 and len(re.sub(r"[^0-9]", "", parts[0])) == 2:
            display = f"{digits[:2]}.{digits[2:]}"
        else:
            display = digits
    else:
        display = digits

    return display, digits


def _is_two_line_plate(boxes: List[_BoxItem]) -> Tuple[bool, List[_BoxItem], List[_BoxItem]]:
    """Phân nhóm các box thành dòng trên (top_line) và dòng dưới (bottom_line).

    Dựa vào tọa độ trục Y và khoảng cách giữa các cụm ký tự.
    """
    valid_boxes = [b for b in boxes if b.text]
    if not valid_boxes:
        return False, [], []

    # Nếu chỉ có 1 box nhưng có ký tự xuống dòng '\n'
    if len(valid_boxes) == 1:
        text = valid_boxes[0].text
        if "\n" in text:
            parts = [p.strip() for p in text.split("\n") if p.strip()]
            if len(parts) >= 2:
                top_b = _BoxItem(0, 0, 10, 10, parts[0], valid_boxes[0].confidence, False)
                bot_b = _BoxItem(0, 15, 10, 25, parts[1], valid_boxes[0].confidence, False)
                return True, [top_b], [bot_b]
        return False, valid_boxes, []

    # Kiểm tra xem các box có tọa độ Y hay không
    boxes_with_coords = [b for b in valid_boxes if b.has_coords]
    if len(boxes_with_coords) < 2:
        # Không có đủ tọa độ: nếu có đúng 2 box, thử phân tích dựa trên cấu trúc text
        if len(valid_boxes) == 2:
            b0_text = clean_plate_string(valid_boxes[0].text)
            b1_text = clean_plate_string(valid_boxes[1].text)
            # Nếu box 0 có chữ cái (sê-ri) và box 1 chủ yếu là số
            b0_has_alpha = any(c.isalpha() for c in b0_text)
            b1_digits_count = sum(c.isdigit() for c in b1_text)
            if b0_has_alpha and b1_digits_count >= 3:
                return True, [valid_boxes[0]], [valid_boxes[1]]
        return False, valid_boxes, []

    # Sắp xếp các box theo trục Y (y_center)
    sorted_by_y = sorted(boxes_with_coords, key=lambda b: b.y_center)
    heights = [b.height for b in sorted_by_y]
    avg_h = sum(heights) / len(heights) if heights else 1.0

    # Tìm khoảng cách Y lớn nhất giữa 2 box kề nhau
    max_gap = 0.0
    split_idx = -1
    for i in range(len(sorted_by_y) - 1):
        gap = sorted_by_y[i + 1].y_center - sorted_by_y[i].y_center
        if gap > max_gap:
            max_gap = gap
            split_idx = i

    # Điều kiện để là 2 dòng:
    # Khoảng cách giữa 2 nhóm tâm Y phải đủ lớn so với chiều cao box
    if split_idx != -1 and max_gap >= 0.35 * avg_h:
        top_group = sorted_by_y[:split_idx + 1]
        bottom_group = sorted_by_y[split_idx + 1:]

        mean_y_top = sum(b.y_center for b in top_group) / len(top_group)
        mean_y_bot = sum(b.y_center for b in bottom_group) / len(bottom_group)

        if (mean_y_bot - mean_y_top) >= 0.45 * avg_h:
            # Sắp xếp các box trong từng dòng theo trục X từ trái sang phải
            top_group.sort(key=lambda b: b.x_min)
            bottom_group.sort(key=lambda b: b.x_min)
            return True, top_group, bottom_group

    # Không thỏa mãn phân chia 2 dòng -> Xếp toàn bộ vào 1 dòng theo trục X
    sorted_by_x = sorted(boxes_with_coords, key=lambda b: b.x_min)
    return False, sorted_by_x, []


def parse_two_line_vietnam_plate(
    ocr_boxes: Union[List[Dict[str, Any]], List[Tuple[Any, ...]]],
    format_style: str = "standard"
) -> Dict[str, Any]:
    """Phân tích & chuẩn hóa biển số 2 dòng xe máy Việt Nam.

    Args:
        ocr_boxes: Danh sách các box từ EasyOCR hoặc detector. Mỗi phần tử có thể là:
            - Tuple EasyOCR: (bbox, text, conf) hoặc (bbox, text)
            - Dict: {"box": [x1, y1, x2, y2], "text": "...", "confidence": ...}
                    hoặc {"bbox": [[x,y],...], "text": "...", "conf": ...}
        format_style: Kiểu định dạng trả về cho trường 'plate_number':
            - "standard" (mặc định): '59K1-12345' (theo quy chuẩn Cục CSGT/Bộ Công An)
            - "display": '59-K1 123.45' (hiển thị trực quan có khoảng cách và dấu)
            - "dotted": '59K1-123.45' (chuẩn hóa có dấu chấm dãy số)

    Returns:
        dict với các thông tin:
            - plate_number: Chuỗi biển số chuẩn hóa theo format_style yêu cầu
            - standard_plate: Dạng chuẩn hóa quy chuẩn '59K1-12345'
            - display_plate: Dạng hiển thị '59-K1 123.45'
            - dotted_plate: Dạng '59K1-123.45'
            - compact_plate: Dạng rút gọn không dấu '59K112345'
            - top_line: Chuỗi dòng trên đã chuẩn hóa (ví dụ '59-K1')
            - bottom_line: Chuỗi dòng dưới đã chuẩn hóa (ví dụ '123.45')
            - confidence: Điểm tin cậy trung bình có trọng số theo độ dài
            - is_two_line: True nếu là biển 2 dòng (xe máy), False nếu 1 dòng (ô tô)
            - raw_text: Chuỗi văn bản thô đọc được
    """
    raw_items = [_extract_box(item) for item in ocr_boxes]
    boxes = [b for b in raw_items if b is not None and b.text.strip()]

    if not boxes:
        return {
            "plate_number": "",
            "standard_plate": "",
            "display_plate": "",
            "dotted_plate": "",
            "compact_plate": "",
            "top_line": "",
            "bottom_line": "",
            "confidence": 0.0,
            "is_two_line": False,
            "raw_text": "",
        }

    is_two_line, top_boxes, bottom_boxes = _is_two_line_plate(boxes)

    # Tính điểm tin cậy trung bình có trọng số theo số ký tự
    total_chars = sum(len(b.text) for b in boxes)
    if total_chars > 0:
        avg_conf = sum(b.confidence * len(b.text) for b in boxes) / total_chars
    else:
        avg_conf = sum(b.confidence for b in boxes) / len(boxes)
    avg_conf = round(avg_conf, 4)

    if is_two_line:
        # Ghép text từng dòng theo thứ tự X
        raw_top_text = "".join(b.text for b in top_boxes)
        raw_bot_text = "".join(b.text for b in bottom_boxes)
        raw_text = f"{raw_top_text}\n{raw_bot_text}"

        norm_top, prov, seri = normalize_top_line(raw_top_text)
        disp_bot, bot_digits = normalize_bottom_line(raw_bot_text)

        # Tạo các định dạng biển số chuẩn hóa
        # Standard: 59K1-12345 (hoặc 59AA-12345)
        # Display:  59-K1 123.45
        # Dotted:   59K1-123.45
        # Compact:  59K112345
        standard_plate = f"{prov}{seri}-{bot_digits}" if (prov and seri and bot_digits) else f"{norm_top}-{disp_bot}"
        display_plate = f"{norm_top} {disp_bot}".strip()
        dotted_plate = f"{prov}{seri}-{disp_bot}" if (prov and seri) else f"{norm_top}-{disp_bot}"
        compact_plate = f"{prov}{seri}{bot_digits}" if (prov and seri) else clean_plate_string(raw_text)

        # Chọn plate_number theo format_style yêu cầu
        if format_style == "display":
            plate_number = display_plate
        elif format_style == "dotted":
            plate_number = dotted_plate
        else:
            plate_number = standard_plate

        return {
            "plate_number": plate_number,
            "standard_plate": standard_plate,
            "display_plate": display_plate,
            "dotted_plate": dotted_plate,
            "compact_plate": compact_plate,
            "top_line": norm_top,
            "bottom_line": disp_bot,
            "confidence": avg_conf,
            "is_two_line": True,
            "raw_text": raw_text,
        }
    else:
        # Biển 1 dòng (ví dụ ô tô dài)
        single_boxes = top_boxes  # chứa toàn bộ boxes đã sort theo X
        raw_text = "".join(b.text for b in single_boxes)
        clean_text = clean_plate_string(raw_text)

        # Giữ format nguyên bản nếu đã chuẩn (ví dụ 51A-123.45)
        plate_number = clean_text
        compact_plate = re.sub(r"[^A-Z0-9]", "", clean_text)

        return {
            "plate_number": plate_number,
            "standard_plate": plate_number,
            "display_plate": plate_number,
            "dotted_plate": plate_number,
            "compact_plate": compact_plate,
            "top_line": plate_number,
            "bottom_line": "",
            "confidence": avg_conf,
            "is_two_line": False,
            "raw_text": raw_text,
        }
