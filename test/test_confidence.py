"""Điểm tin cậy phải là số THẬT — đây là ràng buộc nghiệp vụ, không phải chi tiết kỹ thuật.

Trước ISSUE-003 engine trả hằng số 0.95 cho mọi kết quả, kể cả khi biển số rơi
về "UNKNOWN". Bộ test này khoá lại hành vi mới để không ai lỡ tay khôi phục.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from app.core.vision.engines.anpr_engine import _combine_confidence, _read_with_confidence


class _FakeReader:
    """Đứng thay EasyOCR: trả đúng bộ ba `(bbox, text, conf)` như thư viện thật."""

    def __init__(self, results):
        self._results = results

    def readtext(self, _img):
        return self._results


class CombineConfidenceTest(unittest.TestCase):
    def test_khong_co_detector_thi_lay_nguyen_diem_ocr(self):
        """`None` = chưa nạp được YOLO, khác hẳn với "detector tự tin 0.0"."""
        self.assertEqual(_combine_confidence(None, 0.8), 0.8)

    def test_co_detector_thi_nhan_hai_diem(self):
        self.assertAlmostEqual(_combine_confidence(0.5, 0.8), 0.4)

    def test_detector_khong_tin_thi_ca_luot_khong_dang_tin(self):
        """Đọc chữ chắc nịch trên một vùng ảnh không phải biển số vẫn phải ra điểm thấp."""
        self.assertAlmostEqual(_combine_confidence(0.1, 0.99), 0.099)


class ReadWithConfidenceTest(unittest.TestCase):
    def _read(self, results):
        with patch.dict(
            "app.core.vision.engines.anpr_engine._state",
            {"ocr_reader": _FakeReader(results)},
        ):
            return _read_with_confidence(object())

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


if __name__ == "__main__":
    unittest.main()
