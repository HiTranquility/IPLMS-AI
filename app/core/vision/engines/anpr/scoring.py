"""Điểm tin cậy + chọn kết quả giữa các nhánh đọc (ảnh gốc / ảnh cắt / ảnh làm nét)."""
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from app.core.constants import FALLBACK_PLATE_NUMBER
from app.core.vision.engines.anpr.plate_text import (
    is_plausible_plate_shape,
    is_valid_plate,
    plate_key,
    separator_evidence,
)

# Đọc được đủ cả hai dấu phân cách (vd 51H-988.88) chỉ là bằng chứng định dạng
# MẠNH khi chính lượt đọc đó đủ chắc và detector (nếu có) không đáng ngờ.
STRONG_FORMAT_MIN_OCR_CONF = 0.60
STRONG_FORMAT_MIN_DET_CONF = 0.40


def combine_confidence(det_conf: Optional[float], ocr_conf: float) -> float:
    """Ghép điểm detector và điểm OCR thành một điểm cho cả lượt nhận diện.

    Nhân hai điểm chứ không lấy trung bình: đọc chữ rất chắc trên một vùng ảnh
    mà detector chỉ 30% tin là biển số thì cả lượt vẫn phải đáng ngờ.
    `det_conf is None` = không có detector → điểm cuối chính là điểm OCR.
    """
    if det_conf is None:
        return ocr_conf
    return det_conf * ocr_conf


def has_strong_format_evidence(
    text: str, ocr_confidence: float, detector_confidence: Optional[float]
) -> bool:
    detector_ok = detector_confidence is None or detector_confidence >= STRONG_FORMAT_MIN_DET_CONF
    return (
        separator_evidence(text) == 2
        and ocr_confidence >= STRONG_FORMAT_MIN_OCR_CONF
        and detector_ok
    )


@dataclass(frozen=True)
class PlateCandidate:
    """Một giả thuyết biển số cùng bằng chứng tạo ra nó."""

    text: str
    ocr_confidence: float
    detector_confidence: Optional[float]
    source: str
    image: Any
    is_two_line: bool = False

    @property
    def key(self) -> str:
        return plate_key(self.text)

    @property
    def confidence(self) -> float:
        return combine_confidence(self.detector_confidence, self.ocr_confidence)

    @property
    def strong_format(self) -> bool:
        return has_strong_format_evidence(self.text, self.ocr_confidence, self.detector_confidence)


def select_plate_candidate(candidates: Iterable[PlateCandidate]) -> Optional[PlateCandidate]:
    """Chọn kết quả bằng đồng thuận + confidence, tuyệt đối không bằng độ dài.

    Lỗi thực tế đã gặp: dấu gạch ngang ``-`` trong crop bị EasyOCR đọc thành
    token ``7`` confidence thấp. Chuỗi sai dài hơn một ký tự nên thuật toán cũ
    chọn nó. Ở đây, hai nhánh cùng đọc ra một khoá sẽ thắng một kết quả
    dài nhưng chỉ xuất hiện một lần; khi chưa có đồng thuận thì ưu tiên hình
    dạng hợp lý và điểm tin cậy đo được.
    """
    valid = [
        candidate
        for candidate in candidates
        if candidate.text != FALLBACK_PLATE_NUMBER
        and is_valid_plate(candidate.text)
        and candidate.key
    ]
    if not valid:
        return None

    support = Counter(candidate.key for candidate in valid)
    return max(
        valid,
        key=lambda candidate: (
            support[candidate.key],
            is_plausible_plate_shape(candidate.text),
            candidate.strong_format,
            candidate.confidence,
            candidate.ocr_confidence,
        ),
    )
