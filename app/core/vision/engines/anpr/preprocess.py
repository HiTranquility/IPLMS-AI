"""Chất lượng ảnh cắt + làm nét trước khi OCR lại.

Hai quyết định tách khỏi pipeline vì chúng được chỉnh theo dữ liệu camera thật
(ngưỡng kích thước/độ sáng, tham số lọc) chứ không theo luồng xử lý.
"""
import cv2
import numpy as np
from typing import Optional

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


def detect_plate_color(crop: np.ndarray) -> Optional[str]:
    """Ước lượng màu nền từ crop (white, yellow, blue, red), không suy ra loại xe.

    Phân tích không gian màu HSV trên các pixel nền trung tâm (loại trừ pixel chữ tối màu).
    Chỉ kết luận khi đủ pixel nền; màu không rõ/ảnh tối trả None.
    """
    if not isinstance(crop, np.ndarray) or crop.size == 0 or crop.ndim != 3 or crop.shape[2] != 3:
        return None

    # Lấy vùng trung tâm biển số để tránh dính màu sơn thân vỏ xe ở mép ngoài
    h, w = crop.shape[:2]
    if h >= 30 and w >= 50:
        sample = crop[int(h * 0.15):int(h * 0.85), int(w * 0.15):int(w * 0.85)]
    else:
        sample = crop

    hsv = cv2.cvtColor(sample, cv2.COLOR_BGR2HSV)
    h_ch, s_ch, v_ch = cv2.split(hsv)

    # Loại bỏ các pixel chữ quá tối (V < 60)
    bg_mask = v_ch >= 60
    total_bg = np.count_nonzero(bg_mask)
    if total_bg == 0:
        return None

    # Màu vàng (Yellow - kinh doanh vận tải): Hue 15-38, Saturation >= 60, Value >= 75
    yellow_mask = (h_ch >= 15) & (h_ch <= 38) & (s_ch >= 60) & (v_ch >= 75) & bg_mask
    yellow_ratio = np.count_nonzero(yellow_mask) / total_bg

    # Màu xanh (Blue - cơ quan công quyền): Hue 95-130, Saturation >= 70, Value >= 60
    blue_mask = (h_ch >= 95) & (h_ch <= 130) & (s_ch >= 70) & (v_ch >= 60) & bg_mask
    blue_ratio = np.count_nonzero(blue_mask) / total_bg

    # Màu đỏ (Red - quân đội): Hue <= 10 hoặc >= 170, Saturation >= 75
    red_mask = ((h_ch <= 10) | (h_ch >= 170)) & (s_ch >= 75) & (v_ch >= 60) & bg_mask
    red_ratio = np.count_nonzero(red_mask) / total_bg

    if yellow_ratio >= 0.35 and yellow_ratio > blue_ratio and yellow_ratio > red_ratio:
        return "yellow"
    if blue_ratio >= 0.35 and blue_ratio > yellow_ratio and blue_ratio > red_ratio:
        return "blue"
    if red_ratio >= 0.35 and red_ratio > yellow_ratio and red_ratio > blue_ratio:
        return "red"
    white_ratio = np.count_nonzero((s_ch < 60) & (v_ch >= 120) & bg_mask) / total_bg
    return "white" if white_ratio >= 0.35 else None


def enhance_yellow_plate(crop: np.ndarray) -> np.ndarray:
    """Tối ưu độ tương phản cho biển số màu vàng bằng phép tách kênh (R - B).

    Biển vàng có kênh R cao, G cao, B thấp. Ký tự đen có R, G, B đều thấp.
    Hiệu (R - B) là một ứng viên tiền xử lý; cần đo trên ảnh thật để so chất lượng.
    """
    if not isinstance(crop, np.ndarray) or crop.size == 0 or crop.ndim != 3 or crop.shape[2] != 3:
        return crop
    b, g, r = cv2.split(crop)
    diff = cv2.subtract(r, b)
    norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(norm)
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)


def deskew_plate(crop: np.ndarray) -> np.ndarray:
    """Cân chỉnh góc nghiêng (deskewing) cho biển số bị chụp xéo góc (2° - 35°)."""
    if not isinstance(crop, np.ndarray) or crop.ndim != 3 or crop.shape[2] != 3 or crop.shape[0] < 20 or crop.shape[1] < 40:
        return crop

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150, apertureSize=3)

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return crop

    h, w = crop.shape[:2]
    img_area = w * h

    best_cnt = None
    max_area = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > max_area and area > 0.12 * img_area:
            max_area = area
            best_cnt = cnt

    if best_cnt is None:
        return crop

    rect = cv2.minAreaRect(best_cnt)
    (cx, cy), (rw, rh), angle = rect

    if rw < rh:
        angle = angle + 90.0
    if angle > 45.0:
        angle -= 90.0
    elif angle < -45.0:
        angle += 90.0

    if 2.0 <= abs(angle) <= 35.0:
        center = (w / 2.0, h / 2.0)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        # Expand the OCR canvas instead of cutting characters at the crop edges.
        cos_a, sin_a = abs(M[0, 0]), abs(M[0, 1])
        new_w = int(np.ceil(h * sin_a + w * cos_a))
        new_h = int(np.ceil(h * cos_a + w * sin_a))
        M[0, 2] += new_w / 2.0 - center[0]
        M[1, 2] += new_h / 2.0 - center[1]
        rotated = cv2.warpAffine(
            crop, M, (new_w, new_h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        return rotated

    return crop
