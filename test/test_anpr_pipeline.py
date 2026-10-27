"""Façade `run_anpr`: ảnh bằng chứng trả về backend phải là ẢNH CẮT biển số.

Lỗi đo được 2026-09-25: khi nhánh OCR cả ảnh thắng (điểm cao hơn vì không nhân
điểm detector), `crop_bytes` là NGUYÊN khung hình — backend lưu nó làm bằng
chứng check-in và đem so lúc check-out.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np

from app.core.vision.engines.anpr.engine import run_anpr

_STATE = "app.core.vision.engines.anpr.models._state"


class _Reader:
    def __init__(self, text, conf):
        self._res = [([], text, conf)]
        self.shapes = []
        self.kwargs = []

    def readtext(self, _img, **_kwargs):
        self.shapes.append(_img.shape[:2])
        self.kwargs.append(_kwargs)
        return self._res


class _Tensor:
    def __init__(self, v):
        self._v = np.asarray(v)

    def cpu(self):
        return self

    def numpy(self):
        return self._v


class _Yolo:
    def __init__(self, box, conf):
        self._r = SimpleNamespace(boxes=SimpleNamespace(xyxy=_Tensor([box]), conf=_Tensor([conf])))

    def __call__(self, _img):
        return [self._r]


def _jpeg(width=600, height=300):
    img = np.full((height, width, 3), 200, dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


def _decoded_shape(data):
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR).shape[:2]


class RunAnprEvidenceImageTest(unittest.TestCase):
    def test_full_image_read_wins_but_evidence_is_plate_crop(self):
        # Cả hai nhánh đọc cùng biển; nhánh ảnh gốc có điểm cao hơn (0.67 vs 0.33×0.67).
        state = {
            "ocr_reader": _Reader("59C-888.66", 0.67),
            "yolo_model": _Yolo([100, 50, 476, 238], 0.33),
            "initialized": True,
        }
        with patch.dict(_STATE, state):
            result = run_anpr(_jpeg())
        self.assertEqual("59C-888.66", result["plate_number"])
        self.assertAlmostEqual(0.67, result["confidence"])  # điểm vẫn của nhánh thắng
        self.assertEqual((188, 376), _decoded_shape(result["crop_bytes"]))  # ảnh cắt, không phải 300x600

    def test_strong_crop_read_skips_full_image_ocr(self):
        reader = _Reader("59C-888.66", 0.9)
        state = {
            "ocr_reader": reader,
            "yolo_model": _Yolo([100, 50, 476, 238], 0.8),
            "initialized": True,
        }
        with patch.dict(_STATE, state):
            result = run_anpr(_jpeg())
        self.assertEqual("59C-888.66", result["plate_number"])
        self.assertEqual([(188, 376)], reader.shapes)  # chỉ OCR ảnh cắt, không OCR 300x600
        self.assertIn("allowlist", reader.kwargs[0])

    def test_without_detector_evidence_is_full_image(self):
        state = {"ocr_reader": _Reader("59C-888.66", 0.67), "yolo_model": None, "initialized": True}
        with patch.dict(_STATE, state):
            result = run_anpr(_jpeg())
        self.assertEqual((300, 600), _decoded_shape(result["crop_bytes"]))

    def test_unreadable_plate_falls_back_with_zero_confidence(self):
        state = {"ocr_reader": _Reader("", 0.0), "yolo_model": None, "initialized": True}
        with patch.dict(_STATE, state):
            result = run_anpr(_jpeg())
        self.assertEqual(("UNKNOWN", 0.0), (result["plate_number"], result["confidence"]))


if __name__ == "__main__":
    unittest.main()
