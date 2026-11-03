"""Unit tests cho đợt nâng cấp pipeline ANPR (ISSUE-020):
- Sửa nhầm ký tự chữ/số ở cả 5 số cuối của biển 5 số (1 dòng & 2 dòng) mà vẫn bảo toàn biển 4 số
- Định dạng tường minh `format_vietnam_plate`
- Chẩn đoán cờ chất lượng ảnh cắt `assess_crop_quality` (blurry, glare, skewed, two_line)
- Khử lóa cục bộ `suppress_glare_for_ocr` không làm thay đổi ảnh bằng chứng gốc
"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np

from app.core.vision.engines.anpr.plate_text import (
    correct_plate_confusions,
    format_vietnam_plate,
)
from app.core.vision.engines.anpr.preprocess import (
    assess_crop_quality,
    suppress_glare_for_ocr,
)
from app.core.vision.engines.anpr.engine import run_anpr


class CorrectPlateConfusionsFiveDigitsTest(unittest.TestCase):
    def test_bien_1_dong_5_so_sua_duoc_so_thu_5_tu_cuoi(self):
        # Chữ 'I', 'S', 'B' ở đầu cụm 5 số (sau dấu '-' hoặc trước cụm '.XX') phải đổi thành '1', '5', '8'
        self.assertEqual(correct_plate_confusions("51H-I23.45"), "51H-123.45")
        self.assertEqual(correct_plate_confusions("51H-S2345"), "51H-52345")
        self.assertEqual(correct_plate_confusions("51FB23.45"), "51F823.45")

    def test_bien_2_dong_hoac_seri_2_ky_tu_5_so_sua_du_5_so_cuoi(self):
        self.assertEqual(correct_plate_confusions("59-K1 I23.45"), "59-K1 123.45")
        self.assertEqual(correct_plate_confusions("51LD-B23.45"), "51LD-823.45")
        self.assertEqual(correct_plate_confusions("59-AA S23.45"), "59-AA 523.45")

    def test_bien_4_so_khong_sua_nham_ky_tu_seri_thu_2(self):
        # 'D' trong 51LD-1234 là chữ sê-ri thứ 2, không phải số thứ 5 từ cuối
        self.assertEqual(correct_plate_confusions("51LD-1234"), "51LD-1234")
        self.assertEqual(correct_plate_confusions("50-N1 6789"), "50-N1 6789")


class FormatVietnamPlateTest(unittest.TestCase):
    def test_dinh_dang_bien_1_dong_5_so_va_4_so(self):
        self.assertEqual(format_vietnam_plate("51f17812"), "51F-178.12")
        self.assertEqual(format_vietnam_plate("51f1234"), "51F-1234")

    def test_dinh_dang_bien_2_dong_va_seri_2_ky_tu(self):
        self.assertEqual(format_vietnam_plate("59k112345", is_two_line=True), "59-K1 123.45")
        self.assertEqual(format_vietnam_plate("50n16789", is_two_line=True), "50-N1 6789")
        self.assertEqual(format_vietnam_plate("51ld12345", is_two_line=False), "51LD-123.45")


class AssessCropQualityTest(unittest.TestCase):
    def test_anh_rong_hoac_qua_nho_tra_ve_danh_sach_rong(self):
        self.assertEqual(assess_crop_quality(None), [])
        self.assertEqual(assess_crop_quality(np.zeros((0, 0, 3), dtype=np.uint8)), [])
        self.assertEqual(assess_crop_quality(np.zeros((8, 12, 3), dtype=np.uint8)), [])

    def test_phat_hien_anh_mo_blurry_va_anh_net(self):
        blurry = np.full((60, 240, 3), 140, dtype=np.uint8)
        self.assertIn("blurry", assess_crop_quality(blurry))

        sharp = np.full((60, 240, 3), 230, dtype=np.uint8)
        cv2.putText(sharp, "51F-178.12", (12, 44), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (10, 10, 10), 3)
        self.assertNotIn("blurry", assess_crop_quality(sharp))

    def test_phat_hien_choi_sang_glare(self):
        glare_img = np.full((60, 240, 3), 120, dtype=np.uint8)
        # Vùng chói trắng lóa chiếm 25% diện tích ảnh (V=255, S=0)
        glare_img[:, :60] = (255, 255, 255)
        flags = assess_crop_quality(glare_img)
        self.assertIn("glare", flags)

    def test_phat_hien_goc_nghieng_skewed(self):
        img = np.zeros((120, 240, 3), dtype=np.uint8)
        box = cv2.boxPoints(((120, 60), (200, 60), 12)).astype(np.int32)
        cv2.fillPoly(img, [box], (255, 255, 255))
        flags = assess_crop_quality(img)
        self.assertIn("skewed", flags)

    def test_phat_hien_bien_2_dong_theo_ty_le_khung_hinh(self):
        two_line_crop = np.full((120, 180, 3), 200, dtype=np.uint8)
        one_line_crop = np.full((60, 240, 3), 200, dtype=np.uint8)
        self.assertIn("two_line", assess_crop_quality(two_line_crop))
        self.assertNotIn("two_line", assess_crop_quality(one_line_crop))


class SuppressGlareForOcrTest(unittest.TestCase):
    def test_nen_vung_choi_khong_lam_bien_doi_anh_goc(self):
        crop = np.full((60, 200, 3), 120, dtype=np.uint8)
        crop[:, :80] = (255, 255, 255)
        original = crop.copy()

        result = suppress_glare_for_ocr(crop)
        self.assertEqual(result.shape, crop.shape)
        np.testing.assert_array_equal(crop, original)
        # Vùng chói (255) sau khi nén gamma mềm + CLAHE có giá trị trung bình giảm xuống
        self.assertLess(float(np.mean(result[:, :80])), 255.0)


class RunAnprQualityFlagsIntegrationTest(unittest.TestCase):
    def test_run_anpr_tra_ve_quality_flags_va_goi_suppress_glare_khi_can(self):
        img = np.full((300, 600, 3), 255, dtype=np.uint8)
        ok, buf = cv2.imencode(".jpg", img)
        self.assertTrue(ok)

        class _Tensor:
            def __init__(self, v):
                self._v = np.asarray(v)

            def cpu(self):
                return self

            def numpy(self):
                return self._v

        class _Yolo:
            def __call__(self, _img):
                return [
                    SimpleNamespace(
                        boxes=SimpleNamespace(
                            xyxy=_Tensor([[100, 50, 340, 150]]),
                            conf=_Tensor([0.85]),
                        )
                    )
                ]

        class _Reader:
            def readtext(self, _img, **_kwargs):
                return [([], "51F17812", 0.88)]

        state = {
            "ocr_reader": _Reader(),
            "yolo_model": _Yolo(),
            "initialized": True,
        }
        with patch.dict("app.core.vision.engines.anpr.model_loader._state", state), patch(
            "app.core.vision.engines.anpr.engine.suppress_glare_for_ocr",
            wraps=suppress_glare_for_ocr,
        ) as mock_glare:
            res = run_anpr(buf.tobytes())

        self.assertEqual(res["plate_number"], "51F17812")
        self.assertIn("glare", res["quality_flags"])
        mock_glare.assert_called_once()


if __name__ == "__main__":
    unittest.main()
