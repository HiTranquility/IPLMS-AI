"""Nhánh keyword của hybrid search: OR các từ có nghĩa, không phân biệt dấu."""
import unittest

from app.infra.database.keyword_search import (
    _FOLD_SOURCE,
    _FOLD_TARGET,
    FOLDED_CONTENT_TSVECTOR,
    build_keyword_tsquery,
    fold,
)


class BuildKeywordTsqueryTest(unittest.TestCase):
    def test_cau_hoi_tu_nhien_thanh_or_cac_tu_co_nghia(self):
        self.assertEqual(
            build_keyword_tsquery("Phí gửi xe máy qua đêm là bao nhiêu?"),
            "phi | gui | xe | may | qua | dem",
        )

    def test_go_khong_dau_ra_cung_truy_van(self):
        self.assertEqual(
            build_keyword_tsquery("phi gui xe may qua dem"),
            build_keyword_tsquery("phí gửi xe máy qua đêm"),
        )

    def test_hu_tu_co_dau_khong_nuot_tu_co_nghia_trung_khi_bo_dau(self):
        # "thẻ" bỏ dấu = "the" (trùng hư từ "thế") — vẫn phải giữ.
        self.assertIn("the", build_keyword_tsquery("Thẻ xe bị mất thì sao").split(" | "))

    def test_chi_co_hu_tu_thi_van_tim_bang_chinh_no(self):
        self.assertEqual(build_keyword_tsquery("là gì?"), "la | gi")

    def test_khong_co_tu_nao_thi_none(self):
        self.assertIsNone(build_keyword_tsquery("???"))

    def test_khong_de_ky_tu_dac_biet_cua_tsquery_lot_vao(self):
        self.assertEqual(build_keyword_tsquery("xe & (ô tô) | !"), "xe | o | to")


class FoldTest(unittest.TestCase):
    def test_bo_dau_ca_chu_hoa_va_d_gach(self):
        self.assertEqual(fold("ĐIỀU 5 — Phí Gửi Xe"), "dieu 5 — phi gui xe")

    def test_bang_ky_tu_sql_khop_tung_cap_va_an_toan_de_nhung_vao_sql(self):
        self.assertEqual(len(_FOLD_SOURCE), len(_FOLD_TARGET))
        self.assertNotIn("'", _FOLD_SOURCE + _FOLD_TARGET)
        self.assertIn(f"translate(content, '{_FOLD_SOURCE}', '{_FOLD_TARGET}')", FOLDED_CONTENT_TSVECTOR)


if __name__ == "__main__":
    unittest.main()
