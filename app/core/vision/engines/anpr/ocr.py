"""Đọc chữ bằng EasyOCR kèm điểm tin cậy THẬT."""
from typing import Tuple

from app.core.exceptions import ModelNotLoadedError
from app.core.vision.engines.anpr import models
from app.core.vision.engines.anpr.plate_text import sanitize_plate_text


def read_with_confidence(img) -> Tuple[str, float]:
    """Đọc chữ + điểm tin cậy THẬT của EasyOCR.

    EasyOCR trả `(bbox, text, conf)` cho từng cụm chữ. Gộp điểm theo TRỌNG SỐ
    ĐỘ DÀI: một cụm 1 ký tự đọc chắc chắn không được kéo điểm của cả biển lên.
    Không đọc được cụm nào → 0.0, KHÔNG bịa số.
    """
    reader = models.ocr_reader()
    if reader is None:
        raise ModelNotLoadedError("EasyOCR reader chưa được load.")

    results = reader.readtext(img)
    text_raw = "".join(res[1] for res in results)

    total_chars = sum(len(res[1]) for res in results)
    if total_chars == 0:
        return sanitize_plate_text(text_raw), 0.0

    weighted = sum(float(res[2]) * len(res[1]) for res in results)
    return sanitize_plate_text(text_raw), weighted / total_chars
