"""Điểm tin cậy phải là số THẬT — đây là ràng buộc nghiệp vụ, không phải chi tiết kỹ thuật.

Trước ISSUE-003 engine trả hằng số 0.95 cho mọi kết quả, kể cả khi biển số rơi
về "UNKNOWN". Bộ test này khoá lại hành vi mới để không ai lỡ tay khôi phục.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from app.core.vision.engines.anpr.detector import detect_plate
from app.core.vision.engines.anpr.ocr import read_with_confidence
from app.core.vision.engines.anpr.scoring import (
    PlateCandidate,
    combine_confidence,
    select_plate_candidate,
)
from app.core.exceptions import PlateRecognitionError


class _FakeReader:
    """Đứng thay EasyOCR: trả đúng bộ ba `(bbox, text, conf)` như thư viện thật."""

    def __init__(self, results):
        self._results = results

    def readtext(self, _img):
        return self._results


class _FakeTensor:
    def __init__(self, value):
        self._value = np.asarray(value)

    def cpu(self):
        return self

    def numpy(self):
        return self._value


class _FakeYolo:
    def __init__(self, xyxy, confidence):
        self._result = SimpleNamespace(
            boxes=SimpleNamespace(
                xyxy=_FakeTensor(xyxy),
                conf=_FakeTensor(confidence),
            )
        )

    def __call__(self, _image):
        return [self._result]


class CombineConfidenceTest(unittest.TestCase):
    def test_khong_co_detector_thi_lay_nguyen_diem_ocr(self):
        """`None` = chưa nạp được YOLO, khác hẳn với "detector tự tin 0.0"."""
        self.assertEqual(combine_confidence(None, 0.8), 0.8)

    def test_co_detector_thi_nhan_hai_diem(self):
        self.assertAlmostEqual(combine_confidence(0.5, 0.8), 0.4)

    def test_detector_khong_tin_thi_ca_luot_khong_dang_tin(self):
        """Đọc chữ chắc nịch trên một vùng ảnh không phải biển số vẫn phải ra điểm thấp."""
        self.assertAlmostEqual(combine_confidence(0.1, 0.99), 0.099)


class ReadWithConfidenceTest(unittest.TestCase):
    def _read(self, results):
        with patch.dict(
            "app.core.vision.engines.anpr.models._state",
            {"ocr_reader": _FakeReader(results)},
        ):
            return read_with_confidence(object())

    def test_khong_doc_duoc_cum_nao_thi_diem_bang_0(self):
        text, conf = self._read([])
        self.assertEqual(text, "")
        self.assertEqual(conf, 0.0)

    def test_diem_gop_theo_trong_so_do_dai(self):
        """Cụm 1 ký tự đọc chắc chắn KHÔNG được kéo điểm của cả biển lên."""
        # 8 ký tự @0.50 + 1 ký tự @1.00 -> (0.5*8 + 1.0*1) / 9
        _text, conf = self._read([(None, "51H98888", 0.50), (None, "X", 1.00)])
        self.assertAlmostEqual(conf, 5.0 / 9.0)

    def test_text_duoc_chuan_hoa_va_ghep_lien(self):
        text, _conf = self._read([(None, "51h-988", 0.9), (None, ".88", 0.9)])
        self.assertEqual(text, "51H-988.88")


class SelectPlateCandidateTest(unittest.TestCase):
    def _candidate(self, text, ocr, detector, source):
        return PlateCandidate(text, ocr, detector, source, object())

    def test_dong_thuan_thang_chuoi_dai_hon_nhung_chi_xuat_hien_mot_lan(self):
        """Regression: dấu `-` bị đọc nhầm thành `7` không được thắng vì dài hơn."""
        selected = select_plate_candidate(
            [
                self._candidate("51H988.88", 0.85, None, "full"),
                self._candidate("51H7988.88", 0.82, 0.50, "crop"),
                self._candidate("51H988.88", 0.75, 0.50, "enhanced"),
            ]
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected.text, "51H988.88")

    def test_khong_con_chon_theo_do_dai_khi_chua_co_dong_thuan(self):
        selected = select_plate_candidate(
            [
                self._candidate("51H988.88", 0.85, None, "full"),
                self._candidate("51H7988.88", 0.82, 0.50, "crop"),
            ]
        )

        self.assertEqual(selected.text, "51H988.88")

    def test_crop_co_du_dau_phan_cach_thang_ky_tu_thua_tren_anh_goc(self):
        """Ca đo thật: full đọc dấu `-` thành `7`, crop vẫn nhìn đúng `-` và `.`."""
        selected = select_plate_candidate(
            [
                self._candidate("51H7988.88", 0.70, None, "full"),
                self._candidate("51H-988.88", 0.69, 0.50, "crop"),
            ]
        )

        self.assertEqual(selected.text, "51H-988.88")

    def test_dau_phan_cach_confidence_yeu_khong_duoc_lan_at_bang_chung_tot(self):
        selected = select_plate_candidate(
            [
                self._candidate("51H7988.88", 0.70, None, "full"),
                self._candidate("51H-988.88", 0.20, 0.10, "crop"),
            ]
        )

        self.assertEqual(selected.text, "51H7988.88")

    def test_unknown_khong_duoc_xem_la_mot_bien_so_hop_le(self):
        selected = select_plate_candidate(
            [self._candidate("UNKNOWN", 0.99, None, "full")]
        )

        self.assertIsNone(selected)


class DetectPlateYoloTest(unittest.TestCase):
    def test_chon_box_confidence_cao_nhat_va_crop_trong_bien_anh(self):
        image = np.zeros((6, 6, 3), dtype=np.uint8)
        model = _FakeYolo(
            xyxy=[[-5, -5, 3, 4], [1, 1, 5, 5]],
            confidence=[0.10, 0.90],
        )

        with patch.dict(
            "app.core.vision.engines.anpr.models._state",
            {"yolo_model": model},
        ):
            crop, confidence = detect_plate(image)

        self.assertEqual(crop.shape, (4, 4, 3))
        self.assertAlmostEqual(confidence, 0.90)

    def test_box_nam_ngoai_anh_bi_tu_choi(self):
        image = np.zeros((6, 6, 3), dtype=np.uint8)
        model = _FakeYolo(xyxy=[[10, 10, 12, 12]], confidence=[0.90])

        with patch.dict(
            "app.core.vision.engines.anpr.models._state",
            {"yolo_model": model},
        ):
            with self.assertRaises(PlateRecognitionError):
                detect_plate(image)


if __name__ == "__main__":
    unittest.main()
