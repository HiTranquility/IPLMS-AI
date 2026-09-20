"""Điều phối quality gate và chiến lược chọn mẫu cho một capture."""
from typing import Optional

from app.core.dataset.dtos import CurationResult
from app.core.dataset.engines import inspect_image_quality, select_sample


class CurationService:
    @staticmethod
    def evaluate(
        image_bytes: bytes,
        *,
        model_confidence: Optional[float] = None,
        human_corrected: bool = False,
        random_audit_sample: bool = False,
    ) -> CurationResult:
        quality = inspect_image_quality(image_bytes)
        selected, reasons = select_sample(
            quality,
            model_confidence=model_confidence,
            human_corrected=human_corrected,
            random_audit_sample=random_audit_sample,
        )
        return CurationResult(selected=selected, reasons=reasons, quality=quality)
