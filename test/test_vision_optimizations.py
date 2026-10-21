"""Unit test cho các tối ưu hóa Vision: màu biển số (vàng, trắng, xanh, đỏ), deskew, tách kênh R-B và phân loại xe."""
import unittest
from unittest.mock import patch
import numpy as np
import cv2

from app.core.vision.engines.anpr.preprocess import (
    detect_plate_color,
    enhance_yellow_plate,
    deskew_plate,
)
from app.core.vision.engines.vehicle_classifier import classify_vehicle


class PlateColorDetectionTest(unittest.TestCase):
    def test_no_color_evidence_is_unknown(self):
        for image in (None, np.zeros((0, 0, 3), dtype=np.uint8), np.zeros((30, 70, 3), dtype=np.uint8), np.zeros((30, 70), dtype=np.uint8)):
            self.assertIsNone(detect_plate_color(image))

    def test_nhan_dien_bien_mau_vang(self):
        # Biển vàng kinh doanh: R ~ 240, G ~ 200, B ~ 20 (BGR: 20, 200, 240)
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        img[:] = (20, 200, 240)
        # Thêm ký tự đen ở giữa
        cv2.putText(img, "50H-123.45", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
        color = detect_plate_color(img)
        self.assertEqual(color, "yellow")

    def test_nhan_dien_bien_mau_trang(self):
        # Biển trắng dân sự: BGR ~ (230, 230, 230)
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        img[:] = (230, 230, 230)
        cv2.putText(img, "51F-178.12", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
        color = detect_plate_color(img)
        self.assertEqual(color, "white")

    def test_nhan_dien_bien_mau_xanh(self):
        # Biển xanh cơ quan nhà nước: BGR ~ (200, 100, 20)
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        img[:] = (200, 100, 20)
        cv2.putText(img, "80A-012.34", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        color = detect_plate_color(img)
        self.assertEqual(color, "blue")

    def test_nhan_dien_bien_mau_do(self):
        # Biển đỏ quân đội: BGR ~ (20, 20, 220)
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        img[:] = (20, 20, 220)
        cv2.putText(img, "QA-12.34", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        color = detect_plate_color(img)
        self.assertEqual(color, "red")


class YellowPlateEnhancementTest(unittest.TestCase):
    def test_tach_kenh_r_tru_b_tang_do_tuong_phan(self):
        # Biển vàng: BGR (20, 200, 240), chữ đen (10, 10, 10)
        img = np.zeros((60, 150, 3), dtype=np.uint8)
        img[:] = (20, 200, 240)
        img[20:40, 20:40] = (10, 10, 10)

        enhanced = enhance_yellow_plate(img)
        self.assertEqual(enhanced.shape, (60, 150, 3))
        # Nền phải sáng hơn rất nhiều so với vùng chữ
        bg_val = np.mean(enhanced[5:15, 5:15])
        char_val = np.mean(enhanced[25:35, 25:35])
        self.assertGreater(bg_val, char_val + 50)


class DeskewPlateTest(unittest.TestCase):
    def test_rotated_plate_expands_canvas_and_does_not_mutate_evidence(self):
        img = np.zeros((120, 240, 3), dtype=np.uint8)
        box = cv2.boxPoints(((120, 60), (200, 60), 12)).astype(np.int32)
        cv2.fillPoly(img, [box], (255, 255, 255))
        original = img.copy()
        result = deskew_plate(img)
        self.assertGreater(result.shape[0], img.shape[0])
        self.assertGreaterEqual(result.shape[1], img.shape[1])
        np.testing.assert_array_equal(img, original)

    def test_khong_xoay_khi_bien_thang(self):
        img = np.zeros((80, 200, 3), dtype=np.uint8)
        cv2.rectangle(img, (10, 10), (190, 70), (255, 255, 255), -1)
        res = deskew_plate(img)
        self.assertEqual(res.shape, img.shape)

    def test_anh_qua_nho_giu_nguyen(self):
        tiny = np.zeros((10, 10, 3), dtype=np.uint8)
        res = deskew_plate(tiny)
        self.assertEqual(res.shape, (10, 10, 3))


class VehicleClassifierEvidenceTest(unittest.TestCase):
    def test_missing_model_never_infers_vehicle_from_plate_metadata(self):
        for plate, color in (("59-V1-793.79", "white"), ("50H-123.45", "yellow"), ("51F-178.12", "white")):
            with self.subTest(plate=plate), patch(
                "app.core.vision.engines.vehicle_classifier._ensure_loaded", return_value=False
            ):
                self.assertIsNone(classify_vehicle(b"not-an-image", plate_number=plate, plate_color=color))


if __name__ == "__main__":
    unittest.main()
