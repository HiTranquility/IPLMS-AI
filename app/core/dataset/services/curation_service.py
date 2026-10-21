"""Điều phối quality gate và chiến lược chọn mẫu cho một capture."""
import random
from typing import Callable, Optional

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
        low_confidence_threshold: float = 0.75,
    ) -> CurationResult:
        quality = inspect_image_quality(image_bytes)
        selected, reasons = select_sample(
            quality,
            model_confidence=model_confidence,
            human_corrected=human_corrected,
            random_audit_sample=random_audit_sample,
            low_confidence_threshold=low_confidence_threshold,
        )
        return CurationResult(selected=selected, reasons=reasons, quality=quality)

    @staticmethod
    def evaluate_capture(
        image_bytes: bytes,
        *,
        model_confidence: Optional[float],
        human_corrected: bool,
        low_confidence_threshold: float,
        random_audit_rate: float,
        draw: Callable[[], float] = random.random,
    ) -> CurationResult:
        """Một lượt check-in ở cổng (ISSUE-010): bốc kiểm ngẫu nhiên theo tỉ lệ
        chính sách, rồi áp luật chọn mẫu. `draw` tiêm được để test tất định.

        Bốc ngẫu nhiên cả ảnh máy đọc TỐT — nếu chỉ gom ca khó, bộ dữ liệu lệch
        và không đo được model trên ca thường.
        """
        rate = min(max(random_audit_rate, 0.0), 1.0)
        return CurationService.evaluate(
            image_bytes,
            model_confidence=model_confidence,
            human_corrected=human_corrected,
            random_audit_sample=draw() < rate,
            low_confidence_threshold=low_confidence_threshold,
        )
