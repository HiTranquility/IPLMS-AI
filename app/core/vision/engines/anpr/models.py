"""Nạp model ANPR: YOLO (tìm biển) + EasyOCR (đọc chữ).

Lazy-load ở lần dùng đầu (hoặc warm-up lúc khởi động) thay vì lúc import, để
import module không kéo theo 5–20 giây nạp model (test, script, REST reload).
"""
import threading
from typing import Any, Dict, Optional

from app.config import get_config
from app.infra.ocr.reader import get_easyocr_reader
from app.infra.model_registry import (
    ArtifactResolutionError,
    ModelArtifactSpec,
    get_model_artifact_registry,
)
from app.util.logger import logger

_state: Dict[str, Any] = {
    "yolo_model": None,
    "ocr_reader": None,
    "initialized": False,
}

# Nạp model KHÔNG được chạy hai lần song song, và cờ `initialized` chỉ được bật
# SAU khi nạp xong. Bật trước (bản cũ) khiến request thứ hai đi tiếp với reader
# vẫn là None → FAILED_PRECONDITION ngay sau mỗi lần restart pod.
_load_lock = threading.Lock()


def ensure_models_loaded() -> None:
    """Lazy-load YOLO và EasyOCR reader lần đầu tiên sử dụng (thread-safe)."""
    if _state["initialized"]:
        return

    with _load_lock:
        # Kiểm lại bên trong lock: thread thứ hai chờ ở đây xong thì model đã sẵn.
        if _state["initialized"]:
            return

        vision = get_config().vision

        if _state["ocr_reader"] is None:
            try:
                _state["ocr_reader"] = get_easyocr_reader()
                logger.info(f"EasyOCR loaded: languages={vision.ocr_language_list}")
            except Exception as exc:
                logger.error(f"Failed to load EasyOCR: {exc}")

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
    ensure_models_loaded()
    return _state["ocr_reader"] is not None


def ocr_reader() -> Optional[Any]:
    return _state["ocr_reader"]


def yolo_model() -> Optional[Any]:
    return _state["yolo_model"]


def unload_models() -> dict[str, bool]:
    """Giải phóng YOLO và EasyOCR khỏi RAM/VRAM theo yêu cầu từ Console (Settings/Diagnostics)."""
    import gc

    with _load_lock:
        had_yolo = _state["yolo_model"] is not None
        had_ocr = _state["ocr_reader"] is not None
        _state["yolo_model"] = None
        _state["ocr_reader"] = None
        _state["initialized"] = False
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
    logger.info(f"Vision ANPR models unloaded: had_yolo={had_yolo}, had_ocr={had_ocr}")
    return {"unloaded_yolo": had_yolo, "unloaded_ocr": had_ocr}
