"""Đọc chữ bằng EasyOCR kèm điểm tin cậy THẬT."""
from typing import Tuple

from app.core.constants import PLATE_OCR_ALLOWLIST
from app.core.exceptions import ModelNotLoadedError
from app.core.vision.engines.anpr import models
from app.core.vision.engines.anpr.plate_text import (
    correct_plate_confusions,
    sanitize_plate_text,
)


def _reading_order(results):
    """Xếp cụm chữ theo dòng (trên → dưới) rồi trái → phải.

    Biển xe máy hai dòng (``59-C1`` / ``123.45``): EasyOCR không cam kết thứ tự
    trả về, ghép sai thứ tự là ra ``123.4559-C1``. Cụm thiếu bbox thì giữ nguyên
    thứ tự gốc vì không có gì để xếp.
    """
    if not results or any(not res[0] for res in results):
        return results
    boxes = []
    for res in results:
        ys = [point[1] for point in res[0]]
        xs = [point[0] for point in res[0]]
        boxes.append(((min(ys) + max(ys)) / 2, max(ys) - min(ys), min(xs), res))
    boxes.sort(key=lambda item: item[0])
    lines: list[list] = []
    for center_y, height, left_x, res in boxes:
        if lines and abs(center_y - lines[-1][0][0]) < max(height, lines[-1][0][1]) / 2:
            lines[-1].append((center_y, height, left_x, res))
        else:
            lines.append([(center_y, height, left_x, res)])
    return [item[3] for line in lines for item in sorted(line, key=lambda item: item[2])]


def read_with_confidence(img) -> Tuple[str, float]:
    """Đọc chữ + điểm tin cậy THẬT của EasyOCR.

    EasyOCR trả `(bbox, text, conf)` cho từng cụm chữ. Gộp điểm theo TRỌNG SỐ
    ĐỘ DÀI: một cụm 1 ký tự đọc chắc chắn không được kéo điểm của cả biển lên.
    Không đọc được cụm nào → 0.0, KHÔNG bịa số.
    """
    reader = models.ocr_reader()
    if reader is None:
        raise ModelNotLoadedError("EasyOCR reader chưa được load.")

    results = _reading_order(reader.readtext(img, allowlist=PLATE_OCR_ALLOWLIST))
    text_raw = "".join(res[1] for res in results)

    total_chars = sum(len(res[1]) for res in results)
    text = correct_plate_confusions(sanitize_plate_text(text_raw))
    if total_chars == 0:
        return text, 0.0

    weighted = sum(float(res[2]) * len(res[1]) for res in results)
    return text, weighted / total_chars
