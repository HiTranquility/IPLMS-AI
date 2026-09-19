# core/vision/engines/anpr_engine.py
"""Engine nhận diện biển số xe — YOLO detection + EasyOCR.

Tất cả model (YOLO, EasyOCR reader) được lazy-load lần đầu tiên gọi ``run_anpr``
thay vì load ngay khi import, tránh block startup 5-10 giây khi chưa cần ANPR.
Entrypoint gRPC gọi ``warmup()`` để trả giá nạp model một lần lúc khởi động thay
vì bắt request thật đầu tiên chịu (xem ``app/grpc_server.py``).
"""
import cv2
import numpy as np
import threading
import time
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.config import get_config
from app.core.constants import FALLBACK_PLATE_NUMBER, PLATE_MAX_LENGTH, PLATE_MIN_ALPHA
from app.core.exceptions import PlateRecognitionError, InvalidImageError, ModelNotLoadedError
from app.utils.logger import logger

# ── Lazy-loaded state ─────────────────────────────────────────────────────────

_state: Dict[str, Any] = {
    "yolo_model": None,
    "ocr_reader": None,
    "initialized": False,
}

# Nạp model KHÔNG được chạy hai lần song song, và cờ `initialized` chỉ được bật
# SAU khi nạp xong. Bật trước (bản cũ) khiến request thứ hai đi tiếp với reader
# vẫn là None → FAILED_PRECONDITION ngay sau mỗi lần restart pod.
_load_lock = threading.Lock()


def _get_ai_root() -> Path:
    """Trả về đường dẫn tới thư mục ``ai/`` — gốc của service."""
    return Path(__file__).resolve().parents[4]


def _ensure_models_loaded() -> None:
    """Lazy-load YOLO và EasyOCR reader lần đầu tiên sử dụng (thread-safe)."""
    if _state["initialized"]:
        return

    with _load_lock:
        # Kiểm lại bên trong lock: thread thứ hai chờ ở đây xong thì model đã sẵn.
        if _state["initialized"]:
            return

        vision = get_config().vision

        # ── EasyOCR ──
        try:
            import easyocr
            _state["ocr_reader"] = easyocr.Reader(vision.ocr_language_list)
            logger.info(f"EasyOCR loaded: languages={vision.ocr_language_list}")
        except Exception as exc:
            logger.error(f"Failed to load EasyOCR: {exc}")

        # ── YOLO ──
        model_path = str(_get_ai_root() / vision.yolo_model_path)
        if os.path.exists(model_path):
            try:
                from ultralytics import YOLO
                _state["yolo_model"] = YOLO(model_path)
                logger.info(f"YOLO model loaded: {model_path}")
            except Exception as exc:
                logger.error(f"Failed to load YOLO model: {exc}")
        else:
            logger.warning(f"YOLO model not found: {model_path}")

        _state["initialized"] = True


def warmup() -> bool:
    """Nạp sẵn model lúc khởi động. Trả về True khi OCR reader đã sẵn sàng.

    Gọi từ entrypoint: readiness probe xanh trong khi model chưa nạp là cách
    chắc chắn nhất để k8s bơm traffic vào một pod chưa phục vụ được.
    """
    _ensure_models_loaded()
    return _state["ocr_reader"] is not None


# ── Text processing ──────────────────────────────────────────────────────────

def sanitize_plate_text(text: str) -> str:
    text = text.upper()
    text = re.sub(r'[^A-Z0-9\-.]', '', text)
    return text


def _is_valid_plate(text: str) -> bool:
    """Kiểm tra biển số hợp lệ: tối đa PLATE_MAX_LENGTH ký tự, ít nhất PLATE_MIN_ALPHA chữ cái."""
    return (
        len(text) <= PLATE_MAX_LENGTH
        and len(re.findall(r'[A-Z]', text)) >= PLATE_MIN_ALPHA
    )


# ── Core detection functions ──────────────────────────────────────────────────

def _read_with_confidence(img) -> Tuple[str, float]:
    """Đọc chữ + điểm tin cậy THẬT của EasyOCR.

    EasyOCR trả `(bbox, text, conf)` cho từng cụm chữ. Gộp điểm theo TRỌNG SỐ
    ĐỘ DÀI: một cụm 1 ký tự đọc chắc chắn không được kéo điểm của cả biển lên.
    Không đọc được cụm nào → 0.0, KHÔNG bịa số.
    """
    reader = _state["ocr_reader"]
    if reader is None:
        raise ModelNotLoadedError("EasyOCR reader chưa được load.")

    results = reader.readtext(img)
    text_raw = ''.join(res[1] for res in results)

    total_chars = sum(len(res[1]) for res in results)
    if total_chars == 0:
        return sanitize_plate_text(text_raw), 0.0

    weighted = sum(float(res[2]) * len(res[1]) for res in results)
    return sanitize_plate_text(text_raw), weighted / total_chars


def get_plate_text_from_image(img) -> Tuple[str, float]:
    """Trả `(biển số đã chuẩn hoá, điểm tin cậy OCR)`."""
    return _read_with_confidence(img)


def detect_plate_yolo(img_cv) -> Tuple[Any, Optional[float]]:
    """Trả `(ảnh crop, điểm tin cậy của box)`.

    `None` ở vị trí điểm nghĩa là KHÔNG có detector (chưa nạp được YOLO) — khác
    hẳn với "detector chạy rồi và tự tin 0.0". Người gọi phải phân biệt hai ca
    này, nếu không điểm cuối cùng sẽ bị nhân với 0 một cách oan uổng.
    """
    model = _state["yolo_model"]
    if model is None:
        return img_cv, None
    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    results = model(img_rgb)
    boxes = results[0].boxes
    xyxy = boxes.xyxy.cpu().numpy()
    if len(xyxy) == 0:
        raise PlateRecognitionError("Không phát hiện được biển số")
    x1, y1, x2, y2 = xyxy[0].astype(int)
    crop = img_cv[y1:y2, x1:x2]
    det_conf = float(boxes.conf.cpu().numpy()[0]) if boxes.conf is not None else None
    return crop, det_conf


def enhanced_ocr(plate_crop):
    h, w = plate_crop.shape[:2]
    if w < 100 or h < 80:
        scale_w = 150 / w if w > 0 else 2.0
        scale_h = 100 / h if h > 0 else 2.0
        scale_factor = max(scale_w, scale_h, 2.0)
        plate_crop = cv2.resize(plate_crop, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_LANCZOS4)

    gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
    filtered = cv2.bilateralFilter(gray, d=7, sigmaColor=60, sigmaSpace=60)
    clahe = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(8, 8))
    contrast = clahe.apply(filtered)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(contrast, -1, kernel)

    min_val, max_val = np.min(sharpened), np.max(sharpened)
    if max_val == min_val:
        stretched = sharpened
    else:
        stretched = ((sharpened - min_val) / (max_val - min_val) * 255).astype(np.uint8)

    plate_text, ocr_conf = _read_with_confidence(stretched)
    return plate_text, stretched, ocr_conf


def is_valid_crop(crop_img, min_w=220, min_h=80, min_brightness=80) -> bool:
    if not isinstance(crop_img, np.ndarray):
        return False
    h, w = crop_img.shape[:2]
    if w < min_w or h < min_h:
        return False
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    return np.mean(gray) >= min_brightness


def _combine_confidence(det_conf: Optional[float], ocr_conf: float) -> float:
    """Ghép điểm detector và điểm OCR thành một điểm cho cả lượt nhận diện.

    Nhân hai điểm chứ không lấy trung bình: đọc chữ rất chắc trên một vùng ảnh
    mà detector chỉ 30% tin là biển số thì cả lượt vẫn phải đáng ngờ.
    `det_conf is None` = không có detector → điểm cuối chính là điểm OCR.
    """
    if det_conf is None:
        return ocr_conf
    return det_conf * ocr_conf


# ── Public API ────────────────────────────────────────────────────────────────

def run_anpr(ori_bytes: bytes) -> Dict[str, Any]:
    """Chạy full pipeline ANPR trên raw bytes ảnh.

    Returns:
        dict với keys: ``crop_bytes``, ``plate_number``, ``confidence``,
        ``process_time``. ``confidence`` là điểm THẬT (detector × OCR), bằng
        ``0.0`` khi biển rơi về ``FALLBACK_PLATE_NUMBER``.

    Raises:
        InvalidImageError: ảnh rỗng hoặc không decode được.
        PlateRecognitionError: không nhận diện được biển số hợp lệ.
    """
    _ensure_models_loaded()

    if not ori_bytes:
        raise InvalidImageError("Ảnh đầu vào rỗng.")

    start_time = time.time()
    npimg = np.frombuffer(ori_bytes, np.uint8)
    img_cv = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    if img_cv is None:
        raise InvalidImageError("Không thể decode ảnh đầu vào.")

    full_text, full_conf = get_plate_text_from_image(img_cv)
    if not _is_valid_plate(full_text):
        full_text, full_conf = FALLBACK_PLATE_NUMBER, 0.0
    plate_number = full_text
    processed_image = img_cv
    # Đọc trên ảnh NGUYÊN nên chưa có detector tham gia — điểm chỉ là điểm OCR.
    plate_confidence = full_conf
    det_conf: Optional[float] = None

    crop_text = ""
    enhanced_text = ""

    try:
        plate_crop, det_conf = detect_plate_yolo(img_cv)
        if isinstance(plate_crop, np.ndarray):
            if is_valid_crop(plate_crop):
                crop_text, crop_conf = get_plate_text_from_image(plate_crop)
                if not _is_valid_plate(crop_text):
                    crop_text, crop_conf = "", 0.0
                if len(crop_text) > len(plate_number):
                    plate_number = crop_text
                    processed_image = plate_crop
                    plate_confidence = _combine_confidence(det_conf, crop_conf)
            else:
                enhanced_text, enhanced_img, enhanced_conf = enhanced_ocr(plate_crop)
                if not _is_valid_plate(enhanced_text):
                    enhanced_text, enhanced_conf = "", 0.0
                if len(enhanced_text) > len(plate_number):
                    plate_number = enhanced_text
                    processed_image = enhanced_img
                    plate_confidence = _combine_confidence(det_conf, enhanced_conf)
    except PlateRecognitionError:
        pass
    except Exception as exc:
        logger.warning(f"YOLO/OCR pipeline error (non-fatal): {exc}")

    # Không đọc ra biển thì điểm phải là 0 — trả 0.95 cho chuỗi "UNKNOWN" là cách
    # nhanh nhất để một quyết định mở barie được đưa ra trên thông tin không có.
    if plate_number == FALLBACK_PLATE_NUMBER:
        plate_confidence = 0.0

    if not any([full_text, crop_text, enhanced_text]):
        raise PlateRecognitionError("Không nhận diện được biển số hợp lệ từ ảnh đầu vào.")

    success, buffer = cv2.imencode('.jpg', processed_image)
    if not success:
        raise PlateRecognitionError("Chuyển ảnh crop sang bytes thất bại.")

    crop_bytes = buffer.tobytes()
    process_time = round(time.time() - start_time, 3)

    return {
        "crop_bytes": crop_bytes,
        "plate_number": plate_number,
        "confidence": round(plate_confidence, 4),
        "process_time": process_time,
    }
