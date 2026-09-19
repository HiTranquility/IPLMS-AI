"""Chuẩn hoá chuỗi biển số đọc từ OCR.

Import được `anpr_engine` mà KHÔNG nạp model vì YOLO/EasyOCR đều lazy-load —
nếu ai đó đưa việc nạp model ngược lên module level, bộ test này sẽ chậm hẳn
hoặc chết, và đó là tín hiệu cần sửa.
"""
import unittest

from app.core.constants import PLATE_MAX_LENGTH, PLATE_MIN_ALPHA
from app.core.vision.engines.anpr_engine import _is_valid_plate, sanitize_plate_text


class SanitizePlateTextTest(unittest.TestCase):
    def test_viet_hoa_toan_bo(self):
        self.assertEqual(sanitize_plate_text("51f-178.12"), "51F-178.12")

    def test_bo_ky_tu_ngoai_bang_cho_phep(self):
        self.assertEqual(sanitize_plate_text("51F 178*12"), "51F17812")

    def test_giu_gach_ngang_va_dau_cham(self):
        self.assertEqual(sanitize_plate_text("51F-178.12"), "51F-178.12")

    def test_chuoi_rong(self):
        self.assertEqual(sanitize_plate_text(""), "")


class IsValidPlateTest(unittest.TestCase):
    def test_bien_that_hop_le(self):
        for plate in ("51F-178.12", "65A-004.50", "86A094.70"):
            self.assertTrue(_is_valid_plate(plate), plate)

    def test_qua_dai_bi_loai(self):
        self.assertFalse(_is_valid_plate("A" + "1" * PLATE_MAX_LENGTH))

    def test_khong_co_chu_cai_bi_loai(self):
        self.assertFalse(_is_valid_plate("12345678"))

    def test_chuoi_rong_bi_loai(self):
        self.assertFalse(_is_valid_plate(""))

    def test_du_so_chu_cai_toi_thieu_thi_hop_le(self):
        self.assertGreaterEqual(PLATE_MIN_ALPHA, 1)
        self.assertTrue(_is_valid_plate("A1"))


class DinhDangBienSoVietNamTest(unittest.TestCase):
    """Ghi lại HÀNH VI HIỆN TẠI, không phải hành vi mong muốn.

    OCR đọc được `86A094.70` (thiếu gạch ngang) trong khi biển thật là
    `86A-094.70`. Backend tra xe bằng so khớp CHUỖI CHÍNH XÁC
    (`vehicle.licensePlate = :trimmedPlate`), nên thiếu gạch là không khớp được
    xe của thành viên và bị tính thành khách vãng lai.

    CỐ Ý chưa tự chèn gạch: phải chốt trước là DB lưu biển có gạch hay không,
    rồi chuẩn hoá đồng thời cả hai phía. Test này sẽ đỏ ngay khi ai đó đổi hành
    vi, để việc đổi là có chủ đích.
    """

    def test_hien_tai_khong_tu_chen_gach_ngang(self):
        self.assertEqual(sanitize_plate_text("86A094.70"), "86A094.70")


if __name__ == "__main__":
    unittest.main()
