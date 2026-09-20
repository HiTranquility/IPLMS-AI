"""Chọn mẫu có ích để review; không biến dự đoán máy thành ground truth."""
from typing import Optional, Tuple

from app.core.dataset.dtos import ImageQualityReport


def select_sample(
    quality: ImageQualityReport,
    *,
    model_confidence: Optional[float] = None,
    human_corrected: bool = False,
    random_audit_sample: bool = False,
    low_confidence_threshold: float = 0.75,
) -> Tuple[bool, Tuple[str, ...]]:
    if not quality.decoded:
        return False, ("invalid_image",)

    reasons = []
    if human_corrected:
        reasons.append("human_correction")
    if model_confidence is not None and model_confidence < low_confidence_threshold:
        reasons.append("low_confidence")
    if quality.acceptable and random_audit_sample:
        reasons.append("random_audit")
    if not quality.acceptable and quality.reasons:
        reasons.append("quality_edge_case")

    return bool(reasons), tuple(reasons)
