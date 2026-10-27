"""Cắt đoạn là chỗ quyết định chất lượng retrieval, nên phải có thước đo.

Cắt sai không làm chương trình nổ — nó chỉ làm Copilot trả lời thiếu vế, và kiểu
hỏng đó không ai phát hiện ra cho tới lúc có người đọc kỹ câu trả lời. Test này
khoá lại những tính chất mà thuật toán phải giữ.
"""
import unittest

from app.core.knowledge.constants import CHUNK_MIN_CHARS
from app.core.knowledge.engines.chunker import chunk_text

QUY_CHE = """Quy chế trông giữ xe ban hành kèm quyết định số 12/2026.

Điều 5 - Quy trình xử lý khiếu nại và hoàn phí
Khách hàng có quyền tạo yêu cầu khiếu nại trên ứng dụng trong vòng 48 giờ kể từ
khi kết thúc phiên gửi xe. Bộ phận vận hành phải phản hồi trong 24 giờ làm việc.

Điều 8 - Xử phạt vi phạm nội quy bãi đỗ xe
Đỗ sai ô đã đặt trước: phạt cảnh cáo lần đầu, tái phạm phạt 50.000 đồng.
Chiếm dụng ô sạc xe điện mà không sạc: phụ thu 20.000 đồng mỗi 30 phút.
"""


class CatTheoDieuKhoanTest(unittest.TestCase):
    def test_moi_dieu_khoan_thanh_mot_doan(self):
        chunks = chunk_text(QUY_CHE)
        titles = [c.section_title for c in chunks]
        self.assertIn("Điều 5 - Quy trình xử lý khiếu nại và hoàn phí", titles)
        self.assertIn("Điều 8 - Xử phạt vi phạm nội quy bãi đỗ xe", titles)

    def test_doan_mang_theo_tieu_de_cua_chinh_no(self):
        """Đoạn ghi 'phạt 50.000đ' mà không kèm 'Điều 8 - Xử phạt' thì lúc truy
        vấn không ai biết 50.000đ đó là phạt cái gì."""
        chunks = chunk_text(QUY_CHE)
        doan_phat = next(c for c in chunks if "50.000" in c.content)
        self.assertIn("Điều 8", doan_phat.content)

    def test_khong_bat_nham_tieu_de_nam_giua_cau(self):
        """'theo Điều 5 thì...' là câu văn, không phải ranh giới điều khoản."""
        text = "Bãi xe áp dụng mức phạt theo Điều 5 thì khách phải nộp trong 7 ngày. " * 5
        chunks = chunk_text(text)
        self.assertEqual([None], [c.section_title for c in chunks])

    def test_heading_markdown_cung_duoc_nhan(self):
        text = "# Biểu phí ô tô\n" + "Giờ đầu 20.000 đồng, mỗi giờ tiếp theo 15.000 đồng. " * 4
        chunks = chunk_text(text)
        self.assertEqual("# Biểu phí ô tô", chunks[0].section_title)


class CatKhoiQuaDaiTest(unittest.TestCase):
    def test_khoi_dai_bi_cat_thanh_nhieu_manh(self):
        text = "Một câu quy định dài dòng về việc trông giữ phương tiện. " * 200
        chunks = chunk_text(text, target_chars=800, overlap_chars=100)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk.content), 800)

    def test_co_overlap_giua_hai_manh_lien_tiep(self):
        """Câu nằm vắt qua ranh giới phải còn nguyên vẹn ở ít nhất một mảnh."""
        text = "".join(f"Khoan muc {i} quy dinh ve viec trong giu phuong tien. " for i in range(200))
        chunks = chunk_text(text, target_chars=600, overlap_chars=150)
        duoi = chunks[0].content[-100:]
        self.assertIn(duoi, chunks[1].content)

    def test_mot_doan_van_dai_hon_nguong_van_bi_cat(self):
        """Không có dòng trống nào để bám vào thì vẫn phải cắt được, không trả
        về nguyên khối vượt ngưỡng."""
        text = "x" * 5000
        chunks = chunk_text(text, target_chars=1000, overlap_chars=100)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk.content), 1000)


class TruongHopBienTest(unittest.TestCase):
    def test_text_rong_tra_ve_rong(self):
        self.assertEqual([], chunk_text(""))
        self.assertEqual([], chunk_text("   \n\n  \t "))

    def test_tai_lieu_ngan_van_nap_duoc(self):
        """Một trang biểu phí ngắn vẫn phải vào được kho — thà một đoạn ngắn còn
        hơn im lặng trả về rỗng rồi owner tưởng đã nạp xong."""
        text = "Phí gửi xe máy 6.000 đồng một lượt."
        self.assertLess(len(text), CHUNK_MIN_CHARS)
        chunks = chunk_text(text)
        self.assertEqual(1, len(chunks))
        self.assertIn("6.000", chunks[0].content)

    def test_ordinal_lien_tuc_tu_0(self):
        chunks = chunk_text(QUY_CHE, target_chars=200, overlap_chars=40)
        self.assertEqual(list(range(len(chunks))), [c.ordinal for c in chunks])

    def test_khoang_trang_thua_cua_pdf_duoc_don(self):
        """PDF tách text ra thường kèm khoảng trắng cuối dòng và hàng loạt dòng
        trống; không dọn thì chúng ăn vào hạn mức ký tự của đoạn."""
        text = "Dòng một.   \n   \n\n\n\nDòng hai.   \n"
        chunks = chunk_text(text)
        self.assertNotIn("\n\n\n", chunks[0].content)
        self.assertFalse(chunks[0].content.endswith(" "))



class ChuanHoaUnicodeTest(unittest.TestCase):
    def test_chu_viet_dau_tach_roi_duoc_gop_ve_nfc(self):
        import unicodedata

        decomposed = unicodedata.normalize("NFD", "Phí gửi xe máy là 5.000đ mỗi lượt.")
        [chunk] = chunk_text(decomposed, min_chars=1)
        self.assertEqual(chunk.content, "Phí gửi xe máy là 5.000đ mỗi lượt.")

if __name__ == "__main__":
    unittest.main()
