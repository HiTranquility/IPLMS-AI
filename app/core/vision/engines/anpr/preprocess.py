"""Chất lượng ảnh cắt + làm nét trước khi OCR lại.

Hai quyết định tách khỏi pipeline vì chúng được chỉnh theo dữ liệu camera thật
(ngưỡng kích thước/độ sáng, tham số lọc) chứ không theo luồng xử lý.
"""
import cv2
import numpy as np

# Ảnh cắt nhỏ/tối hơn ngưỡng này thì OCR thô thường hỏng → đi thẳng nhánh làm nét.
MIN_CROP_WIDTH = 220
MIN_CROP_HEIGHT = 80
MIN_CROP_BRIGHTNESS = 80

# Ảnh nhỏ hơn ngưỡng này được phóng to trước khi lọc (EasyOCR đọc kém chữ < ~30px).
_UPSCALE_BELOW_WIDTH = 100
_UPSCALE_BELOW_HEIGHT = 80
_UPSCALE_TARGET_WIDTH = 150
_UPSCALE_TARGET_HEIGHT = 100
_UPSCALE_MIN_FACTOR = 2.0

# Khử nhiễu giữ biên → tăng tương phản cục bộ → làm nét.
_BILATERAL = dict(d=7, sigmaColor=60, sigmaSpace=60)
_CLAHE_CLIP_LIMIT = 1.8
_CLAHE_TILE_GRID = (8, 8)
_SHARPEN_KERNEL = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])


def is_valid_crop(
    crop_img,
    min_w: int = MIN_CROP_WIDTH,
    min_h: int = MIN_CROP_HEIGHT,
    min_brightness: int = MIN_CROP_BRIGHTNESS,
) -> bool:
    if not isinstance(crop_img, np.ndarray):
        return False
    h, w = crop_img.shape[:2]
    if w < min_w or h < min_h:
        return False
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    return np.mean(gray) >= min_brightness


def enhance_for_ocr(plate_crop):
    """Phóng to (nếu nhỏ) → xám → khử nhiễu → CLAHE → làm nét → kéo giãn tương phản."""
    h, w = plate_crop.shape[:2]
    if w < _UPSCALE_BELOW_WIDTH or h < _UPSCALE_BELOW_HEIGHT:
        scale_w = _UPSCALE_TARGET_WIDTH / w if w > 0 else _UPSCALE_MIN_FACTOR
        scale_h = _UPSCALE_TARGET_HEIGHT / h if h > 0 else _UPSCALE_MIN_FACTOR
        scale_factor = max(scale_w, scale_h, _UPSCALE_MIN_FACTOR)
        plate_crop = cv2.resize(
            plate_crop, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_LANCZOS4
        )

    gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
    filtered = cv2.bilateralFilter(gray, **_BILATERAL)
    clahe = cv2.createCLAHE(clipLimit=_CLAHE_CLIP_LIMIT, tileGridSize=_CLAHE_TILE_GRID)
    contrast = clahe.apply(filtered)
    sharpened = cv2.filter2D(contrast, -1, _SHARPEN_KERNEL)

    min_val, max_val = np.min(sharpened), np.max(sharpened)
    if max_val == min_val:
        return sharpened
    return ((sharpened - min_val) / (max_val - min_val) * 255).astype(np.uint8)
