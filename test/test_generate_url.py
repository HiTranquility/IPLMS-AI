"""Tên file ảnh phải khoá theo event_id, không chỉ theo biển số."""
import unittest

from app.util.generate_url import (
    generate_cropped_image_url,
    generate_original_image_url,
    sanitize_plate,
)


class SanitizePlateTest(unittest.TestCase):
    def test_giu_chu_so_gach_gach_duoi(self):
        self.assertEqual(sanitize_plate("51F-178.12"), "51F-17812")

    def test_bo_khoang_trang_va_ky_tu_la(self):
        self.assertEqual(sanitize_plate("51 F/178"), "51F178")

    def test_rong_hoac_none_ve_unknown(self):
        self.assertEqual(sanitize_plate(""), "unknown")
        self.assertEqual(sanitize_plate(None), "unknown")

    def test_chuoi_toan_ky_tu_la_ve_unknown(self):
        self.assertEqual(sanitize_plate("///"), "unknown")


class ImageUrlTest(unittest.TestCase):
    """Đây là hồi quy cho lỗi thật: mọi xe không đọc được biển đều rơi về
    FALLBACK_PLATE_NUMBER, nên nếu tên file chỉ theo biển số thì chúng ghi đè
    chung một file và VerifyVehicleMatch lúc check-out đối chiếu nhầm ảnh xe khác.
    """

    def test_hai_xe_khong_doc_duoc_bien_ra_hai_file_khac_nhau(self):
        a = generate_cropped_image_url("UNKNOWN", "evt_aaaaaaaaaaaa")
        b = generate_cropped_image_url("UNKNOWN", "evt_bbbbbbbbbbbb")
        self.assertNotEqual(a, b)

    def test_cung_bien_vao_bai_hai_luot_ra_hai_file_khac_nhau(self):
        a = generate_cropped_image_url("51F-178.12", "evt_111111111111")
        b = generate_cropped_image_url("51F-178.12", "evt_222222222222")
        self.assertNotEqual(a, b)

    def test_duong_dan_va_hau_to_dung_quy_uoc(self):
        url = generate_cropped_image_url("51F-178.12", "evt_abc123abc123")
        self.assertEqual(url, "/static/cropped/51F-17812_evt_abc123abc123_crop.jpg")

    def test_anh_goc_va_anh_crop_khong_dung_chung_ten(self):
        event_id = "evt_abc123abc123"
        self.assertNotEqual(
            generate_cropped_image_url("51F", event_id),
            generate_original_image_url("51F", event_id),
        )


if __name__ == "__main__":
    unittest.main()
