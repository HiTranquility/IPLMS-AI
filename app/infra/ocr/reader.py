"""Load one EasyOCR reader per process for ANPR and document OCR."""
import threading
from typing import Any

from app.config import get_config

_reader: Any | None = None
_lock = threading.Lock()


def get_easyocr_reader() -> Any:
    global _reader
    if _reader is not None:
        return _reader
    with _lock:
        if _reader is None:
            import easyocr

            vision = get_config().vision
            kwargs = {}
            if vision.ocr_model_storage_dir.strip():
                kwargs["model_storage_directory"] = vision.ocr_model_storage_dir
            _reader = easyocr.Reader(vision.ocr_language_list, **kwargs)
    return _reader
