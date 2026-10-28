"""Parser là cửa nhận file từ người ngoài, nên test tập trung vào lối vào xấu.

Nhánh PDF/DOCX cần `pypdf` / `python-docx` — chưa cài thì tự bỏ qua, và tự chạy
lại khi đã cài. Nhánh TXT/MD cùng toàn bộ phép kiểm đầu vào thì không phụ thuộc
gói nào, chạy được ngay.
"""
import importlib.util
import os
import unittest

from app.core.constants import KNOWLEDGE_MAX_FILE_BYTES
from app.core.knowledge.constants import CHUNK_MIN_CHARS
from app.core.enums import DocumentFormat
from app.core.exceptions import (
    DocumentTooLargeError,
    NoTextLayerError,
    UnsupportedFormatError,
)
from app.core.knowledge.engines.document_parser import parse_document

CO_PYPDF = importlib.util.find_spec("pypdf") is not None
CO_DOCX = importlib.util.find_spec("docx") is not None


class VanBanThuanTest(unittest.TestCase):
    def test_doc_duoc_txt_tieng_viet(self):
        noi_dung = "Điều 1 - Phí gửi xe máy là 6.000 đồng một lượt."
        ket_qua = parse_document(noi_dung.encode("utf-8"), "quy_che.txt")
        self.assertEqual(DocumentFormat.TXT, ket_qua.doc_format)
        self.assertIn("6.000", ket_qua.text)
        self.assertEqual([], ket_qua.warnings)

    def test_markdown_nhan_ca_hai_duoi(self):
        for ten in ("noi_quy.md", "noi_quy.markdown"):
            with self.subTest(ten=ten):
                ket_qua = parse_document(b"# Noi quy bai xe", ten)
                self.assertEqual(DocumentFormat.MARKDOWN, ket_qua.doc_format)

    def test_file_khong_phai_utf8_van_doc_duoc_kem_canh_bao(self):
        """Từ chối cả file vì vài byte lạ thì owner không hiểu vì sao và cũng
        không sửa được — giải mã bỏ qua ký tự hỏng rồi cảnh báo là đủ."""
        ket_qua = parse_document(b"Phi gui xe \xff\xfe 6000 dong", "bang_gia.txt")
        self.assertTrue(ket_qua.text)
        self.assertEqual(1, len(ket_qua.warnings))
        self.assertIn("UTF-8", ket_qua.warnings[0])

    def test_txt_khong_co_khai_niem_so_trang(self):
        self.assertIsNone(parse_document(b"abc xyz", "a.txt").page_count)


class ChanDauVaoXauTest(unittest.TestCase):
    def test_duoi_file_la_bi_tu_choi(self):
        with self.assertRaises(UnsupportedFormatError):
            parse_document(b"MZ\x90\x00", "virus.exe")

    def test_khong_co_duoi_file_cung_bi_tu_choi(self):
        with self.assertRaises(UnsupportedFormatError):
            parse_document(b"noi dung gi do", "khong_co_duoi")

    def test_khong_tin_phan_mo_rong__pdf_gia(self):
        """Tên file là thứ người ngoài đặt. Đặt tên .pdf cho file không phải PDF
        phải bị chặn TRƯỚC khi nó tới tay pypdf."""
        with self.assertRaises(UnsupportedFormatError) as ctx:
            parse_document(b"day khong phai PDF dau", "gia_mao.pdf")
        self.assertIn("không khớp phần mở rộng", str(ctx.exception))

    def test_khong_tin_phan_mo_rong__docx_gia(self):
        with self.assertRaises(UnsupportedFormatError):
            parse_document(b"khong phai file zip", "gia_mao.docx")

    def test_file_rong(self):
        with self.assertRaises(NoTextLayerError):
            parse_document(b"", "trong.txt")

    def test_file_chi_co_khoang_trang_coi_nhu_khong_co_chu(self):
        """Nếu cứ đi tiếp, owner sẽ được báo 'đã nạp xong' cho một tài liệu
        không có chữ nào."""
        with self.assertRaises(NoTextLayerError):
            parse_document(b"   \n\n  \t  \n ", "trong.txt")

    def test_vuot_tran_kich_thuoc(self):
        qua_to = b"x" * (KNOWLEDGE_MAX_FILE_BYTES + 1)
        with self.assertRaises(DocumentTooLargeError):
            parse_document(qua_to, "to_qua.txt")

    def test_dung_bang_tran_thi_van_qua(self):
        vua_du = b"x" * KNOWLEDGE_MAX_FILE_BYTES
        self.assertTrue(parse_document(vua_du, "vua_du.txt").text)

    def test_tran_thap_hon_gioi_han_grpc(self):
        """[GOTCHA] grpc_max_message_length đúng 10MB. File đúng 10MB cộng phần
        khung message sẽ bị gRPC chặn, nên trần tài liệu phải nhỏ hơn hẳn."""
        self.assertLess(KNOWLEDGE_MAX_FILE_BYTES, 10 * 1024 * 1024)


@unittest.skipUnless(CO_PYPDF and os.getenv("AI_TEST_OCR"), "Cần pypdf + AI_TEST_OCR=1")
class PdfTest(unittest.TestCase):
    def test_pdf_hop_le_nhung_khong_co_lop_van_ban(self):
        """PDF scan: cấu trúc đúng, chữ ký đúng, nhưng không có chữ nào."""
        from pypdf import PdfWriter

        import io as _io
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        buf = _io.BytesIO()
        writer.write(buf)

        with self.assertRaises(NoTextLayerError):
            parse_document(buf.getvalue(), "ban_scan.pdf")

    def test_pdf_scan_co_chu_duoc_ocr_thanh_ban_nhap(self):
        """A raster-only PDF must yield text instead of being treated as empty."""
        import io as _io
        from PIL import Image, ImageDraw, ImageFont
        from pypdf import PdfReader

        image = Image.new("RGB", (2300, 1350), "white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=90)
        draw.text((100, 140), "PARKING RULES", fill="black", font=font)
        draw.text((100, 360), "MOTORBIKE FEE 25000 VND", fill="black", font=font)
        draw.text((100, 580), "CAR FEE 50000 VND PER HOUR", fill="black", font=font)
        draw.text((100, 800), "OPEN FROM SIX AM TO TEN PM", fill="black", font=font)
        draw.text((100, 1020), "KEEP YOUR TICKET AT ALL TIMES", fill="black", font=font)
        buf = _io.BytesIO()
        image.save(buf, "PDF", resolution=150)
        self.assertFalse(PdfReader(_io.BytesIO(buf.getvalue())).pages[0].extract_text())

        parsed = parse_document(buf.getvalue(), "scanned-rules.pdf")
        self.assertGreaterEqual(len(parsed.text.strip()), CHUNK_MIN_CHARS)
        self.assertTrue(any("nhận dạng chữ từ ảnh" in warning for warning in parsed.warnings))


@unittest.skipUnless(CO_DOCX, "Chưa cài python-docx")
class DocxTest(unittest.TestCase):
    def test_lay_ca_noi_dung_trong_bang(self):
        """Bảng biểu phí là thứ đáng giá nhất trong quy chế, mà `paragraphs`
        KHÔNG bao gồm nội dung bảng."""
        import io as _io

        import docx

        tai_lieu = docx.Document()
        tai_lieu.add_paragraph("Biểu phí gửi xe")
        bang = tai_lieu.add_table(rows=1, cols=2)
        bang.rows[0].cells[0].text = "Xe máy"
        bang.rows[0].cells[1].text = "6000 đồng"
        buf = _io.BytesIO()
        tai_lieu.save(buf)

        ket_qua = parse_document(buf.getvalue(), "bieu_phi.docx")
        self.assertIn("Biểu phí gửi xe", ket_qua.text)
        self.assertIn("Xe máy", ket_qua.text)
        self.assertIn("6000", ket_qua.text)


def _treo_mai():
    """Giả lập PDF độc làm pypdf treo. Ở cấp module để process con (spawn) import được."""
    import time
    while True:
        time.sleep(1)


def _bao_loi_dinh_dang():
    raise UnsupportedFormatError("File PDF được đặt mật khẩu nên không đọc được nội dung.")


class XuLyCachLyTest(unittest.TestCase):
    """bug-026: bước pypdf chạy trong process con, quá hạn thì bị GIẾT — thread thì không giết được."""

    def test_process_treo_bi_giet_khi_qua_han(self):
        import multiprocessing
        import time
        from app.core.knowledge.engines.document_parser import _run_isolated

        bat_dau = time.perf_counter()
        with self.assertRaises(DocumentTooLargeError):
            _run_isolated(_treo_mai, (), timeout=2)
        self.assertLess(time.perf_counter() - bat_dau, 15)
        self.assertEqual([], [p for p in multiprocessing.active_children() if p.is_alive()])

    def test_loi_nghiep_vu_tra_ve_dung_kieu(self):
        from app.core.knowledge.engines.document_parser import _run_isolated

        with self.assertRaises(UnsupportedFormatError) as raised:
            _run_isolated(_bao_loi_dinh_dang, (), timeout=30)
        self.assertIn("mật khẩu", str(raised.exception))

    @unittest.skipUnless(CO_PYPDF, "Cần pypdf")
    def test_pdf_co_lop_chu_doc_qua_process_con(self):
        duong_dan = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge", "demo-upload", "04-an-ninh-demo.pdf")
        with open(duong_dan, "rb") as f:
            ket_qua = parse_document(f.read(), "an-ninh.pdf")
        self.assertEqual(DocumentFormat.PDF, ket_qua.doc_format)
        self.assertGreater(len(ket_qua.text.strip()), 20)
        self.assertGreaterEqual(ket_qua.page_count, 1)

    def test_gioi_han_ocr_toi_da_20_trang(self):
        from app.core.knowledge.constants import DOCUMENT_PARSE_TIMEOUT_SECONDS
        from app.core.knowledge.engines.document_parser import _PDF_OCR_MAX_PAGES
        self.assertEqual(_PDF_OCR_MAX_PAGES, 20)
        self.assertEqual(DOCUMENT_PARSE_TIMEOUT_SECONDS, 300.0)

    def test_pdf_can_ocr_vuot_qua_20_trang_thi_bao_loi(self):
        from unittest.mock import patch
        from app.core.knowledge.engines.document_parser import _tach_pdf, UnsupportedFormatError
        with patch("app.core.knowledge.engines.document_parser._run_isolated", return_value=([""] * 21, list(range(21)), [], 21)):
            with self.assertRaises(UnsupportedFormatError) as cm:
                _tach_pdf(b"%PDF-1.4 mock")
            self.assertIn("vượt giới hạn 20 trang", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
