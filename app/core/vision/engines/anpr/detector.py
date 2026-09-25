"""YOLO tìm vùng biển số → ảnh cắt + điểm tin cậy của box."""
from typing import Any, Optional, Tuple

import cv2
import numpy as np

from app.core.exceptions import PlateRecognitionError
from app.core.vision.engines.anpr import models


def detect_plate(img_cv) -> Tuple[Any, Optional[float]]:
    """Trả `(ảnh crop, điểm tin cậy của box)`.

    `None` ở vị trí điểm nghĩa là KHÔNG có detector (chưa nạp được YOLO) — khác
    hẳn với "detector chạy rồi và tự tin 0.0". Người gọi phải phân biệt hai ca
    này, nếu không điểm cuối cùng sẽ bị nhân với 0 một cách oan uổng.
    """
    model = models.yolo_model()
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
