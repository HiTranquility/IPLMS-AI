"""Unit tests cho bộ phân tích & chuẩn hóa biển số 2 dòng xe máy Việt Nam và AnprOnnxEngine.

Kiểm thử:
1. Biển số xe máy 2 dòng TP.HCM (59-K1, 50-N1, 59-AA)
2. Biển số xe máy 2 dòng Hà Nội (29-B1, 30-H2)
3. Biển số xe máy 2 dòng Đà Nẵng (43-C1, 43-D1)
4. Biển số 1 dòng ô tô (51A-123.45, 30F-999.99)
5. Sửa lỗi nhầm ký tự chữ/số (OCR Confusions)
6. Dòng trên tách cụm nhiều box
7. Edge cases (chuỗi rỗng, một box có \\n, format styles)
8. AnprOnnxEngine (fallback an toàn & mock ONNX inference)
"""
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from app.core.vision.engines.anpr.two_line_plate_parser import (
    normalize_bottom_line,
    normalize_top_line,
    parse_two_line_vietnam_plate,
)
from app.core.vision.engines.anpr.onnx_engine import AnprOnnxEngine


class TwoLinePlateParserTPHCMTest(unittest.TestCase):
    """Kiểm thử biển số xe máy 2 dòng TP.HCM (Mã 50-59)."""

    def test_tphcm_standard_5_digits(self):
        # Biển 59-K1 / 123.45 (EasyOCR polygon format)
        boxes = [
            ([[10, 10], [90, 10], [90, 45], [10, 45]], "59-K1", 0.95),
            ([[15, 55], [85, 55], [85, 90], [15, 90]], "123.45", 0.98),
        ]
        result = parse_two_line_vietnam_plate(boxes)
        self.assertTrue(result["is_two_line"])
        self.assertEqual("59K1-12345", result["plate_number"])
        self.assertEqual("59-K1 123.45", result["display_plate"])
        self.assertEqual("59-K1", result["top_line"])
        self.assertEqual("123.45", result["bottom_line"])
        self.assertAlmostEqual(0.9664, result["confidence"], places=3)

    def test_tphcm_4_digits_compact(self):
        # Biển 50-N1 / 6789 (Dict format)
        boxes = [
            {"box": [10, 10, 90, 45], "text": "50-N1", "confidence": 0.92},
            {"box": [15, 55, 85, 90], "text": "6789", "confidence": 0.96},
        ]
        result = parse_two_line_vietnam_plate(boxes)
        self.assertTrue(result["is_two_line"])
        self.assertEqual("50N1-6789", result["plate_number"])
        self.assertEqual("50-N1 6789", result["display_plate"])
        self.assertEqual("50-N1", result["top_line"])
        self.assertEqual("6789", result["bottom_line"])

    def test_tphcm_electric_or_under50cc(self):
        # Biển 59-AA / 123.45 (xe dưới 50cc hoặc xe điện sê-ri 2 chữ cái)
        boxes = [
            ([[10, 10], [90, 10], [90, 45], [10, 45]], "59-AA", 0.94),
            ([[15, 55], [85, 55], [85, 90], [15, 90]], "123.45", 0.97),
        ]
        result = parse_two_line_vietnam_plate(boxes)
        self.assertTrue(result["is_two_line"])
        self.assertEqual("59AA-12345", result["plate_number"])
        self.assertEqual("59-AA 123.45", result["display_plate"])


class TwoLinePlateParserHaNoiTest(unittest.TestCase):
    """Kiểm thử biển số xe máy 2 dòng Hà Nội (Mã 29-33)."""

    def test_hanoi_29_b1_repeat_digits(self):
        boxes = [
            ([[10, 12], [88, 12], [88, 42], [10, 42]], "29-B1", 0.93),
            ([[12, 54], [88, 54], [88, 86], [12, 86]], "888.88", 0.97),
        ]
        result = parse_two_line_vietnam_plate(boxes)
        self.assertTrue(result["is_two_line"])
        self.assertEqual("29B1-88888", result["plate_number"])
        self.assertEqual("29-B1 888.88", result["display_plate"])
        self.assertEqual("29-B1", result["top_line"])
        self.assertEqual("888.88", result["bottom_line"])

    def test_hanoi_30_h2_4_digits(self):
        boxes = [
            {"box": [10, 10, 80, 40], "text": "30-H2", "confidence": 0.91},
            {"box": [10, 50, 80, 80], "text": "1234", "confidence": 0.95},
        ]
        result = parse_two_line_vietnam_plate(boxes)
        self.assertTrue(result["is_two_line"])
        self.assertEqual("30H2-1234", result["plate_number"])
        self.assertEqual("30-H2 1234", result["display_plate"])


class TwoLinePlateParserDaNangTest(unittest.TestCase):
    """Kiểm thử biển số xe máy 2 dòng Đà Nẵng (Mã 43)."""

    def test_danang_43_c1_repeat_digits(self):
        boxes = [
            ([[10, 15], [95, 15], [95, 45], [10, 45]], "43-C1", 0.96),
            ([[12, 58], [92, 58], [92, 92], [12, 92]], "999.99", 0.99),
        ]
        result = parse_two_line_vietnam_plate(boxes)
        self.assertTrue(result["is_two_line"])
        self.assertEqual("43C1-99999", result["plate_number"])
        self.assertEqual("43-C1 999.99", result["display_plate"])
        self.assertEqual("43-C1", result["top_line"])
        self.assertEqual("999.99", result["bottom_line"])

    def test_danang_43_d1_standard(self):
        boxes = [
            {"box": [20, 20, 100, 50], "text": "43-D1", "confidence": 0.94},
            {"box": [20, 60, 100, 90], "text": "123.45", "confidence": 0.98},
        ]
        result = parse_two_line_vietnam_plate(boxes)
        self.assertTrue(result["is_two_line"])
        self.assertEqual("43D1-12345", result["plate_number"])


class OneLineCarPlateTest(unittest.TestCase):
    """Kiểm thử biển số 1 dòng ô tô (dài) - không bị nhầm thành 2 dòng."""

    def test_car_plate_single_box(self):
        # Biển ô tô nằm trọn trong 1 box
        boxes = [
            ([[10, 20], [200, 20], [200, 60], [10, 60]], "51A-123.45", 0.95),
        ]
        result = parse_two_line_vietnam_plate(boxes)
        self.assertFalse(result["is_two_line"])
        self.assertEqual("51A-123.45", result["plate_number"])
        self.assertEqual("51A-123.45", result["top_line"])
        self.assertEqual("", result["bottom_line"])

    def test_car_plate_multiple_horizontal_boxes(self):
        # Biển ô tô bị tách thành 2 cụm ngang hàng Y (y_center như nhau)
        boxes = [
            ([[10, 20], [70, 20], [70, 55], [10, 55]], "30F-", 0.94),
            ([[80, 20], [160, 20], [160, 55], [80, 55]], "999.99", 0.96),
        ]
        result = parse_two_line_vietnam_plate(boxes)
        self.assertFalse(result["is_two_line"])
        self.assertEqual("30F-999.99", result["plate_number"])


class OcrConfusionCorrectionTest(unittest.TestCase):
    """Kiểm thử cơ chế sửa nhầm chữ/số đặc trưng của OCR trên biển 2 dòng."""

    def test_correct_letter_to_digit_in_province_and_numbers(self):
        # S9 -> 59 (S đọc nhầm từ 5)
        # I23.4S -> 123.45 (I -> 1, S -> 5)
        boxes = [
            ([[10, 10], [90, 10], [90, 45], [10, 45]], "S9-K1", 0.88),
            ([[15, 55], [85, 55], [85, 90], [15, 90]], "I23.4S", 0.85),
        ]
        result = parse_two_line_vietnam_plate(boxes)
        self.assertTrue(result["is_two_line"])
        self.assertEqual("59K1-12345", result["plate_number"])
        self.assertEqual("59-K1 123.45", result["display_plate"])

    def test_correct_digit_to_letter_in_series(self):
        # Dòng trên 59-01 -> 0 đọc nhầm từ D (59-D1)
        boxes = [
            ([[10, 10], [90, 10], [90, 45], [10, 45]], "59-01", 0.89),
            ([[15, 55], [85, 55], [85, 90], [15, 90]], "456.78", 0.95),
        ]
        result = parse_two_line_vietnam_plate(boxes)
        self.assertTrue(result["is_two_line"])
        self.assertEqual("59D1-45678", result["plate_number"])


class MultiBoxSplitTest(unittest.TestCase):
    """Kiểm thử khi dòng trên bị tách thành các box rời rạc ('59' và 'K1')."""

    def test_top_line_split_into_two_boxes(self):
        boxes = [
            ([[10, 10], [45, 10], [45, 45], [10, 45]], "59", 0.95),
            ([[50, 10], [90, 10], [90, 45], [50, 45]], "K1", 0.94),
            ([[15, 55], [85, 55], [85, 90], [15, 90]], "123.45", 0.98),
        ]
        result = parse_two_line_vietnam_plate(boxes)
        self.assertTrue(result["is_two_line"])
        self.assertEqual("59K1-12345", result["plate_number"])
        self.assertEqual("59-K1 123.45", result["display_plate"])


class EdgeCasesAndFormatStylesTest(unittest.TestCase):
    """Kiểm thử các trường hợp biên và các kiểu định dạng format_style."""

    def test_empty_boxes(self):
        result = parse_two_line_vietnam_plate([])
        self.assertFalse(result["is_two_line"])
        self.assertEqual("", result["plate_number"])
        self.assertEqual(0.0, result["confidence"])

    def test_newline_in_single_box(self):
        boxes = ["59-K1\n123.45"]
        result = parse_two_line_vietnam_plate(boxes)
        self.assertTrue(result["is_two_line"])
        self.assertEqual("59K1-12345", result["plate_number"])

    def test_format_styles(self):
        boxes = [
            ([[10, 10], [90, 10], [90, 45], [10, 45]], "59-K1", 0.95),
            ([[15, 55], [85, 55], [85, 90], [15, 90]], "123.45", 0.98),
        ]
        res_std = parse_two_line_vietnam_plate(boxes, format_style="standard")
        self.assertEqual("59K1-12345", res_std["plate_number"])

        res_disp = parse_two_line_vietnam_plate(boxes, format_style="display")
        self.assertEqual("59-K1 123.45", res_disp["plate_number"])

        res_dot = parse_two_line_vietnam_plate(boxes, format_style="dotted")
        self.assertEqual("59K1-123.45", res_dot["plate_number"])


class AnprOnnxEngineTest(unittest.TestCase):
    """Kiểm thử AnprOnnxEngine và cơ chế fallback an toàn."""

    def test_engine_fallback_when_onnx_not_found(self):
        engine = AnprOnnxEngine(model_path="non_existent_model.onnx")
        self.assertFalse(engine.is_using_onnx())

    @patch("app.core.vision.engines.anpr.detector.detect_plate")
    def test_detect_plate_calls_fallback_pytorch(self, mock_pt_detect):
        dummy_crop = np.zeros((50, 100, 3), dtype=np.uint8)
        mock_pt_detect.return_value = (dummy_crop, 0.88)

        engine = AnprOnnxEngine(model_path="non_existent_model.onnx")
        test_img = np.zeros((200, 200, 3), dtype=np.uint8)
        crop, conf = engine.detect_plate(test_img)

        self.assertEqual(0.88, conf)
        self.assertEqual((50, 100, 3), crop.shape)
        mock_pt_detect.assert_called_once()

    def test_mock_onnx_session_detection(self):
        """Mock một ONNX InferenceSession để xác nhận luồng inference ONNX và NMS."""
        engine = AnprOnnxEngine(model_path="dummy.onnx")
        # Giả lập ONNX runtime khả dụng
        mock_session = MagicMock()
        mock_input = MagicMock()
        mock_input.name = "images"
        mock_output = MagicMock()
        mock_output.name = "output0"
        mock_session.get_inputs.return_value = [mock_input]
        mock_session.get_outputs.return_value = [mock_output]

        # Tạo output giả lập của YOLO: (1, 5, 8400)
        # 1 box phát hiện tại trung tâm với score 0.95
        dummy_pred = np.zeros((1, 5, 8400), dtype=np.float32)
        # cx, cy, w, h
        dummy_pred[0, 0, 0] = 320.0
        dummy_pred[0, 1, 0] = 320.0
        dummy_pred[0, 2, 0] = 100.0
        dummy_pred[0, 3, 0] = 50.0
        # score
        dummy_pred[0, 4, 0] = 0.95

        mock_session.run.return_value = [dummy_pred]

        engine.session = mock_session
        engine.input_name = "images"
        engine.output_names = ["output0"]
        engine.is_onnx_available = True

        self.assertTrue(engine.is_using_onnx())

        test_img = np.full((480, 640, 3), 120, dtype=np.uint8)
        crop, conf = engine.detect_plate(test_img)

        self.assertIsNotNone(crop)
        self.assertAlmostEqual(0.95, conf, places=2)
        mock_session.run.assert_called_once()


    def test_latency_measurement(self):
        engine = AnprOnnxEngine(model_path="dummy.onnx")
        latency = engine.measure_latency(iterations=2)
        self.assertIsInstance(latency, float)
        self.assertGreaterEqual(latency, 0.0)


class RunAnprTwoLineIntegrationTest(unittest.TestCase):
    """Kiểm thử tích hợp từ facade run_anpr với biển 2 dòng xe máy."""

    def test_run_anpr_integrates_two_line_plate(self):
        import cv2
        from app.core.vision.engines.anpr.engine import run_anpr

        dummy_img = np.full((300, 600, 3), 200, dtype=np.uint8)
        ok, buf = cv2.imencode(".jpg", dummy_img)
        self.assertTrue(ok)

        mock_boxes = [
            ([[10, 10], [90, 10], [90, 45], [10, 45]], "59-K1", 0.95),
            ([[15, 55], [85, 55], [85, 90], [15, 90]], "123.45", 0.98),
        ]

        class _MotorbikeReader:
            def readtext(self, _img, **_kwargs):
                return mock_boxes

        state = {
            "ocr_reader": _MotorbikeReader(),
            "yolo_model": None,
            "initialized": True,
        }
        with patch.dict("app.core.vision.engines.anpr.models._state", state):
            res = run_anpr(buf.tobytes())

        self.assertTrue(res["is_two_line"])
        self.assertEqual("59K1-12345", res["plate_number"])
        self.assertAlmostEqual(0.9664, res["confidence"], places=3)


if __name__ == "__main__":
    unittest.main()
