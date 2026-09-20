"""Đo chất lượng kỹ thuật của ảnh trước khi đề xuất review hoặc train."""
import cv2
import numpy as np

from app.core.dataset.dtos import ImageQualityReport


def inspect_image_quality(
    image_bytes: bytes,
    *,
    min_width: int = 160,
    min_height: int = 120,
    min_brightness: float = 25.0,
    max_brightness: float = 235.0,
    min_blur_score: float = 20.0,
) -> ImageQualityReport:
    if not image_bytes:
        return ImageQualityReport(False, 0, 0, 0.0, 0.0, False, ("empty",))

    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return ImageQualityReport(False, 0, 0, 0.0, 0.0, False, ("decode_failed",))

    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    reasons = []
    if width < min_width or height < min_height:
        reasons.append("too_small")
    if brightness < min_brightness:
        reasons.append("too_dark")
    if brightness > max_brightness:
        reasons.append("too_bright")
    if blur_score < min_blur_score:
        reasons.append("too_blurry")

    return ImageQualityReport(
        decoded=True,
        width=width,
        height=height,
        brightness=round(brightness, 4),
        blur_score=round(blur_score, 4),
        acceptable=not reasons,
        reasons=tuple(reasons),
    )
