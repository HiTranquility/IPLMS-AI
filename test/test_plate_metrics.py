"""Thước đo của bộ vàng phải đúng TRƯỚC khi ai tin vào con số nó in ra.

Import `training.plate_metrics` — module hàm thuần, KHÔNG nạp model, nên bộ test
vẫn xong trong vài mili-giây. Ai đó đưa `cv2`/`torch` vào module đó thì test này
chậm hẳn, và đó là tín hiệu cần sửa.
"""
import unittest

from training.plate_metrics import (
    aggregate,
    char_error_rate,
    group_by_tag,
    levenshtein,
    normalize_relaxed,
    normalize_strict,
    percentile,
    score_one,
)


class NormalizeTest(unittest.TestCase):
    def test_strict_giu_dau_phan_cach(self):
        self.assertEqual(normalize_strict(" 51f-178.12 "), "51F-178.12")

    def test_relaxed_bo_gach_cham_va_khoang_trang(self):
        self.assertEqual(normalize_relaxed("51F-178.12"), "51F17812")
        self.assertEqual(normalize_relaxed("51F 178 12"), "51F17812")

    def test_none_thanh_chuoi_rong(self):
        self.assertEqual(normalize_strict(None), "")
        self.assertEqual(normalize_relaxed(None), "")


class LevenshteinTest(unittest.TestCase):
    def test_giong_het(self):
        self.assertEqual(levenshtein("51F17812", "51F17812"), 0)

    def test_mot_ky_tu_sai(self):
        self.assertEqual(levenshtein("51F17812", "51F17B12"), 1)

    def test_chuoi_rong(self):
        self.assertEqual(levenshtein("", "ABC"), 3)
        self.assertEqual(levenshtein("ABC", ""), 3)


class CharErrorRateTest(unittest.TestCase):
    def test_doc_dung_ky_tu_chi_thieu_gach_thi_cer_bang_0(self):
        """Đây là ca thật của OCR hiện tại — CER phải nói "không sai ký tự nào"."""
        self.assertEqual(char_error_rate("51F-178.12", "51F17812"), 0.0)

    def test_sai_mot_ky_tu_tren_tam(self):
        self.assertAlmostEqual(char_error_rate("51F17812", "51F17B12"), 1 / 8)

    def test_khong_doc_ra_gi_thi_cer_bang_1(self):
        self.assertEqual(char_error_rate("51F-178.12", ""), 1.0)

    def test_nhan_that_rong_la_loi_du_lieu(self):
        self.assertEqual(char_error_rate("", ""), 0.0)
        self.assertEqual(char_error_rate("", "51F17812"), 1.0)

    def test_doan_dai_hon_nhan_thi_cer_vuot_1(self):
        """Cố ý KHÔNG cắt trần — kết quả rác phải trông đúng như rác."""
        self.assertGreater(char_error_rate("51F", "51F1781299999"), 1.0)


class ScoreOneTest(unittest.TestCase):
    def test_thieu_gach_thi_relaxed_dung_strict_sai(self):
        row = score_one("51F-178.12", "51F17812")
        self.assertFalse(row["exact_strict"])
        self.assertTrue(row["exact_relaxed"])
        self.assertEqual(row["cer"], 0.0)

    def test_khop_nguyen_van_thi_ca_hai_dung(self):
        row = score_one("51F-178.12", "51F-178.12")
        self.assertTrue(row["exact_strict"])
        self.assertTrue(row["exact_relaxed"])

    def test_khong_doc_ra_gi_thi_khong_tinh_la_khop(self):
        row = score_one("51F-178.12", None)
        self.assertFalse(row["exact_strict"])
        self.assertFalse(row["exact_relaxed"])

    def test_nhan_rong_va_doan_rong_van_khong_tinh_la_khop(self):
        """Hai chuỗi rỗng bằng nhau về mặt chuỗi, nhưng đó không phải một lượt đọc đúng."""
        row = score_one("", None)
        self.assertFalse(row["exact_relaxed"])


class PercentileTest(unittest.TestCase):
    def test_lay_gia_tri_co_that_khong_noi_suy(self):
        values = [0.1, 0.2, 0.9]
        self.assertIn(percentile(values, 0.95), values)

    def test_danh_sach_rong(self):
        self.assertEqual(percentile([], 0.5), 0.0)

    def test_mot_phan_tu(self):
        self.assertEqual(percentile([0.42], 0.95), 0.42)


class AggregateTest(unittest.TestCase):
    def _rows(self):
        return [
            {**score_one("51F-178.12", "51F17812"), "confidence": 0.9, "process_time": 1.0, "tags": ["day"]},
            {**score_one("65A-004.50", "65A-004.50"), "confidence": 0.8, "process_time": 2.0, "tags": ["day"]},
            {**score_one("86A-094.70", None), "confidence": 0.0, "process_time": None, "error": "mờ", "tags": ["night"]},
        ]

    def test_bo_rong(self):
        summary = aggregate([])
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["exact_match_strict"], 0.0)

    def test_luot_khong_doc_ra_gi_van_nam_trong_mau_so(self):
        """Bỏ qua lượt thất bại là cách chắc chắn nhất để bịa ra một con số đẹp."""
        summary = aggregate(self._rows())
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["recognized"], 2)
        self.assertAlmostEqual(summary["recognition_rate"], 2 / 3)

    def test_strict_thap_hon_relaxed_khi_thieu_gach(self):
        summary = aggregate(self._rows())
        self.assertAlmostEqual(summary["exact_match_strict"], 1 / 3)
        self.assertAlmostEqual(summary["exact_match_relaxed"], 2 / 3)

    def test_dem_loi_va_do_latency(self):
        summary = aggregate(self._rows())
        self.assertEqual(summary["errors"], 1)
        self.assertEqual(summary["latency_p95"], 2.0)

    def test_confidence_trung_binh(self):
        summary = aggregate(self._rows())
        self.assertAlmostEqual(summary["mean_confidence"], (0.9 + 0.8 + 0.0) / 3)


class GroupByTagTest(unittest.TestCase):
    def test_tach_theo_dieu_kien_anh(self):
        rows = [
            {**score_one("51F-178.12", "51F-178.12"), "tags": ["day"]},
            {**score_one("86A-094.70", None), "tags": ["night"]},
        ]
        by_tag = group_by_tag(rows)
        self.assertEqual(by_tag["day"]["exact_match_strict"], 1.0)
        self.assertEqual(by_tag["night"]["exact_match_strict"], 0.0)

    def test_anh_khong_tag_khong_lot_vao_bang_nao(self):
        self.assertEqual(group_by_tag([{**score_one("51F", "51F"), "tags": []}]), {})


if __name__ == "__main__":
    unittest.main()
