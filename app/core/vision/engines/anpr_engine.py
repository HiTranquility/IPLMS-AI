# core/vision/engines/anpr_engine.py
"""Façade ANPR — phối hợp các tầng trong `engines/anpr/`, không tự làm việc của tầng nào.

Luồng một ảnh: YOLO cắt biển → (ảnh cắt đủ tốt?) OCR ảnh cắt → (chưa có bằng
chứng định dạng mạnh?) OCR cả ảnh → (chưa đọc được / hai nhánh bất đồng?) làm nét
rồi OCR lại → chọn bằng đồng thuận.
Chi tiết từng bước nằm ở module tương ứng (xem `engines/anpr/__init__.py`).
"""
import time
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from app.core.constants import FALLBACK_PLATE_NUMBER
from app.core.exceptions import InvalidImageError, PlateRecognitionError
from app.core.vision.engines.anpr import models
from app.core.vision.engines.anpr.detector import detect_plate
from app.core.vision.engines.anpr.ocr import read_plate_details, read_with_confidence
from app.core.vision.engines.anpr.plate_text import is_valid_plate, plate_key
from app.core.vision.engines.anpr.preprocess import (
    enhance_for_ocr, is_valid_crop, detect_plate_color, enhance_yellow_plate, deskew_plate,
)
from app.core.vision.engines.anpr.scoring import PlateCandidate, select_plate_candidate
from app.core.vision.engines.anpr_onnx_engine import AnprOnnxEngine
from app.core.vision.engines.two_line_plate_parser import parse_two_line_vietnam_plate
from app.util.logger import logger

warmup = models.warmup
_onnx_engine: Optional[AnprOnnxEngine] = None


def get_anpr_detector() -> AnprOnnxEngine:
    global _onnx_engine
    if _onnx_engine is None:
        _onnx_engine = AnprOnnxEngine()
    return _onnx_engine


__all__ = ["run_anpr", "warmup", "AnprOnnxEngine", "parse_two_line_vietnam_plate"]


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
    models.ensure_models_loaded()

    if not ori_bytes:
        raise InvalidImageError("Ảnh đầu vào rỗng.")

    start_time = time.perf_counter()
    img_cv = cv2.imdecode(np.frombuffer(ori_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img_cv is None:
        raise InvalidImageError("Không thể decode ảnh đầu vào.")

    candidates: List[PlateCandidate] = []

    # Ảnh cắt biển số thật từ detector — dùng làm ảnh BẰNG CHỨNG (check-in/out,
    # khiếu nại) dù chữ cuối cùng lấy từ nhánh nào.
    plate_crop: Optional[np.ndarray] = None
    crop_is_valid = False
    crop_candidate: Optional[PlateCandidate] = None
    det_conf: Optional[float] = None
    try:
        crop, det_conf = get_anpr_detector().detect_plate(img_cv)
        # Không có detector: detect_plate trả đúng object ảnh gốc. Không OCR lại
        # cùng ảnh rồi tính đó là một "nhánh đồng thuận" độc lập giả.
        if isinstance(crop, np.ndarray) and not (det_conf is None and crop is img_cv):
            plate_crop = crop
            crop_is_valid = is_valid_crop(crop)
            if crop_is_valid:
                crop_text, crop_conf, crop_is_2line, _ = read_plate_details(crop)
                if is_valid_plate(crop_text):
                    crop_candidate = PlateCandidate(
                        crop_text, crop_conf, det_conf, "crop", crop, is_two_line=crop_is_2line
                    )
                    candidates.append(crop_candidate)
    except PlateRecognitionError:
        pass
    except Exception as exc:
        logger.warning(f"YOLO/OCR pipeline error (non-fatal): {exc}")

    # OCR cả khung hình là bước đắt nhất và dễ đọc nhầm chữ biển hiệu. Ảnh cắt
    # đã đọc ra biển đủ hai dấu phân cách với điểm tốt thì không cần "trọng tài".
    full_text = ""
    if crop_candidate is None or not crop_candidate.strong_format:
        full_text, full_conf, full_is_2line, _ = read_plate_details(img_cv)
        if is_valid_plate(full_text):
            candidates.append(
                PlateCandidate(full_text, full_conf, None, "full", img_cv, is_two_line=full_is_2line)
            )

    if plate_crop is not None:
        try:
            # Làm nét vốn đắt. Chỉ chạy khi ảnh cắt chưa đủ chất lượng / không đọc
            # được, hoặc ảnh gốc và ảnh cắt bất đồng — đúng lúc cần "trọng tài".
            full_key = plate_key(full_text) if is_valid_plate(full_text) else ""
            should_enhance = (
                not crop_is_valid
                or crop_candidate is None
                or (
                    bool(full_key)
                    and full_key != crop_candidate.key
                    # Ảnh cắt đã đọc được cả hai dấu phân cách là bằng chứng định
                    # dạng mạnh. Không trả thêm 3-6 giây CPU chỉ để xác nhận lại.
                    and not crop_candidate.strong_format
                )
            )
            if should_enhance:
                ocr_crop = deskew_plate(plate_crop)
                if detect_plate_color(plate_crop) == "yellow":
                    ocr_crop = enhance_yellow_plate(ocr_crop)
                enhanced_img = enhance_for_ocr(ocr_crop)
                enhanced_text, enhanced_conf, enh_is_2line, _ = read_plate_details(enhanced_img)
                if is_valid_plate(enhanced_text):
                    candidates.append(
                        PlateCandidate(
                            enhanced_text, enhanced_conf, det_conf, "enhanced", enhanced_img, is_two_line=enh_is_2line
                        )
                    )
        except Exception as exc:
            logger.warning(f"Enhance/OCR pipeline error (non-fatal): {exc}")

    selected = select_plate_candidate(candidates)
    if selected is None:
        plate_number = FALLBACK_PLATE_NUMBER
        plate_confidence = 0.0
        is_two_line = False
    else:
        plate_number = selected.text
        plate_confidence = selected.confidence
        is_two_line = getattr(selected, "is_two_line", False)

    # Trước đây trả `selected.image`: khi nhánh ảnh gốc thắng, "ảnh crop" gửi về
    # backend là NGUYÊN khung hình (đo 2026-09-25: ảnh 600x300 thay vì biển
    # 376x188), còn khi nhánh làm nét thắng thì là ảnh xám đã xử lý. Backend lưu
    # ảnh này làm bằng chứng check-in và đem so lúc check-out → phải là ảnh cắt
    # MÀU GỐC của biển số. Chỉ khi detector không tìm được biển mới dùng ảnh gốc.
    evidence_image = plate_crop if plate_crop is not None else img_cv

    success, buffer = cv2.imencode(".jpg", evidence_image)
    if not success:
        raise PlateRecognitionError("Chuyển ảnh crop sang bytes thất bại.")

    return {
        "crop_bytes": buffer.tobytes(),
        "plate_number": plate_number,
        "confidence": round(plate_confidence, 4),
        "process_time": round(time.perf_counter() - start_time, 3),
        "is_two_line": is_two_line,
        # No detector crop means no observed plate background. Never infer from vehicle paint.
        "plate_color": detect_plate_color(plate_crop) if plate_crop is not None else None,
    }
