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
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

from app.config import get_config
from app.core.constants import FALLBACK_PLATE_NUMBER, PLATE_MAX_LENGTH, PLATE_MIN_ALPHA
from app.core.exceptions import PlateRecognitionError, InvalidImageError, ModelNotLoadedError
from app.infra.model_registry import (
    ArtifactResolutionError,
    ModelArtifactSpec,
    get_model_artifact_registry,
)
from app.util.logger import logger

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
        if _state["ocr_reader"] is None:
            try:
                import easyocr
                ocr_kwargs = {}
                if vision.ocr_model_storage_dir.strip():
                    ocr_kwargs["model_storage_directory"] = vision.ocr_model_storage_dir
                _state["ocr_reader"] = easyocr.Reader(vision.ocr_language_list, **ocr_kwargs)
                logger.info(f"EasyOCR loaded: languages={vision.ocr_language_list}")
            except Exception as exc:
                logger.error(f"Failed to load EasyOCR: {exc}")

        # ── YOLO ──
        if _state["yolo_model"] is None:
            _load_yolo(vision)

        # CHỈ đánh dấu xong khi OCR đã nạp. Bật cờ cả lúc OCR lỗi (bản cũ) biến một
        # lỗi tạm thời — vd. gRPC và REST cùng tải model vào chung `temp.zip` của
        # EasyOCR, một bên mất file — thành tiến trình hỏng VĨNH VIỄN tới lúc restart
        # (bug-006). Để False thì request kế tiếp tự thử nạp lại.
        _state["initialized"] = _state["ocr_reader"] is not None


def _load_yolo(vision) -> None:
    """YOLO là tầng tuỳ chọn: thiếu nó thì OCR chạy trên cả ảnh (`det_conf=None`)."""
    try:
        model_path = get_model_artifact_registry().resolve(
            ModelArtifactSpec(
                name="plate-detector",
                version=vision.yolo_model_version,
                file_name="best.pt",
                local_path=vision.yolo_model_path,
                source_url=vision.yolo_artifact_url,
                sha256=vision.yolo_artifact_sha256,
            )
        )
        from ultralytics import YOLO
        _state["yolo_model"] = YOLO(str(model_path))
        logger.info(f"YOLO model loaded: {model_path}")
    except ArtifactResolutionError as exc:
        logger.warning(f"YOLO model artifact unavailable: {exc}")
    except Exception as exc:
        logger.error(f"Failed to load YOLO model: {exc}")


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


def _plate_key(text: str) -> str:
    """Khoá dùng để so kết quả giữa các nhánh OCR.

    Dấu ``-``/``.`` thường biến mất sau resize hoặc threshold. Chúng vẫn được
    giữ trong kết quả trả về, nhưng không nên làm hai lần đọc cùng một biển bị
    xem là hai kết quả khác nhau.
    """
    return re.sub(r"[^A-Z0-9]", "", sanitize_plate_text(text))


@dataclass(frozen=True)
class _PlateCandidate:
    """Một giả thuyết biển số cùng bằng chứng tạo ra nó."""

    text: str
    ocr_confidence: float
    detector_confidence: Optional[float]
    source: str
    image: Any

    @property
    def key(self) -> str:
        return _plate_key(self.text)

    @property
    def confidence(self) -> float:
        return _combine_confidence(self.detector_confidence, self.ocr_confidence)


def _is_plausible_plate_shape(text: str) -> bool:
    """Điểm cộng mềm cho hình dạng thường gặp, không thay validation hiện tại."""
    key = _plate_key(text)
    digits = sum(char.isdigit() for char in key)
    letters = sum(char.isalpha() for char in key)
    return 7 <= len(key) <= 10 and digits >= 5 and letters >= PLATE_MIN_ALPHA


def _separator_evidence(text: str) -> int:
    """Số dấu phân cách OCR thật sự nhìn thấy, không tự suy diễn/chèn thêm."""
    return int("-" in text) + int("." in text)


def _has_strong_format_evidence(candidate: _PlateCandidate) -> bool:
    """Chỉ coi dấu là bằng chứng mạnh khi cả OCR lẫn detector đủ dùng."""
    detector_ok = (
        candidate.detector_confidence is None
        or candidate.detector_confidence >= 0.40
    )
    return (
        _separator_evidence(candidate.text) == 2
        and candidate.ocr_confidence >= 0.60
        and detector_ok
    )


def _select_plate_candidate(candidates: Iterable[_PlateCandidate]) -> Optional[_PlateCandidate]:
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
        and _is_valid_plate(candidate.text)
        and candidate.key
    ]
    if not valid:
        return None

    support = Counter(candidate.key for candidate in valid)
    return max(
        valid,
        key=lambda candidate: (
            support[candidate.key],
            _is_plausible_plate_shape(candidate.text),
            _has_strong_format_evidence(candidate),
            candidate.confidence,
            candidate.ocr_confidence,
        ),
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

    confidences = boxes.conf.cpu().numpy() if boxes.conf is not None else None
    best_index = int(np.argmax(confidences)) if confidences is not None else 0
    x1, y1, x2, y2 = xyxy[best_index].astype(int)
    height, width = img_cv.shape[:2]
    x1, x2 = max(0, x1), min(width, x2)
    y1, y2 = max(0, y1), min(height, y2)
    if x2 <= x1 or y2 <= y1:
        raise PlateRecognitionError("Vùng biển số detector trả về không hợp lệ")

    crop = img_cv[y1:y2, x1:x2]
    det_conf = float(confidences[best_index]) if confidences is not None else None
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
        PlateRecognitionError: không encode được ảnh kết quả.
    """
    _ensure_models_loaded()

    if not ori_bytes:
        raise InvalidImageError("Ảnh đầu vào rỗng.")

    start_time = time.time()
    npimg = np.frombuffer(ori_bytes, np.uint8)
    img_cv = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    if img_cv is None:
        raise InvalidImageError("Không thể decode ảnh đầu vào.")

    candidates = []
    full_text, full_conf = get_plate_text_from_image(img_cv)
    if _is_valid_plate(full_text):
        candidates.append(
            _PlateCandidate(full_text, full_conf, None, "full", img_cv)
        )

    crop_text = ""
    crop_conf = 0.0
    enhanced_text = ""

    try:
        plate_crop, det_conf = detect_plate_yolo(img_cv)
        # Không có detector: detect_plate_yolo trả đúng object ảnh gốc. Không
        # OCR lại cùng ảnh rồi tính đó là một "nhánh đồng thuận" độc lập giả.
        if isinstance(plate_crop, np.ndarray) and not (
            det_conf is None and plate_crop is img_cv
        ):
            crop_is_valid = is_valid_crop(plate_crop)
            if crop_is_valid:
                crop_text, crop_conf = get_plate_text_from_image(plate_crop)
                if _is_valid_plate(crop_text):
                    candidates.append(
                        _PlateCandidate(crop_text, crop_conf, det_conf, "crop", plate_crop)
                    )
                else:
                    crop_text = ""

            # Enhance vốn đắt. Chỉ chạy khi crop chưa đủ chất lượng/không đọc
            # được, hoặc ảnh gốc và crop bất đồng — đúng lúc cần "trọng tài".
            full_key = _plate_key(full_text) if _is_valid_plate(full_text) else ""
            crop_key = _plate_key(crop_text) if _is_valid_plate(crop_text) else ""
            crop_format_is_strong = (
                _separator_evidence(crop_text) == 2
                and crop_conf >= 0.60
                and (det_conf is None or det_conf >= 0.40)
            ) if crop_key else False
            should_enhance = (
                not crop_is_valid
                or not crop_key
                or (
                    bool(full_key)
                    and full_key != crop_key
                    # Crop đã đọc được cả hai dấu phân cách là bằng chứng định
                    # dạng mạnh. Không trả thêm 3-6 giây CPU chỉ để xác nhận lại.
                    and not crop_format_is_strong
                )
            )
            if should_enhance:
                enhanced_text, enhanced_img, enhanced_conf = enhanced_ocr(plate_crop)
                if _is_valid_plate(enhanced_text):
                    candidates.append(
                        _PlateCandidate(
                            enhanced_text,
                            enhanced_conf,
                            det_conf,
                            "enhanced",
                            enhanced_img,
                        )
                    )
                else:
                    enhanced_text = ""
    except PlateRecognitionError:
        pass
    except Exception as exc:
        logger.warning(f"YOLO/OCR pipeline error (non-fatal): {exc}")

    selected = _select_plate_candidate(candidates)
    if selected is None:
        plate_number = FALLBACK_PLATE_NUMBER
        plate_confidence = 0.0
        processed_image = img_cv
    else:
        plate_number = selected.text
        plate_confidence = selected.confidence
        processed_image = selected.image

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
