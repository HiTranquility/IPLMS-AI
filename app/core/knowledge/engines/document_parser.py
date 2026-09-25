"""Tách văn bản thuần từ tài liệu owner tải lên (PDF · DOCX · TXT · MD).

Ba điều đáng nói về thiết kế ở đây:

1. **Không tin phần mở rộng.** Tên file là thứ người ngoài đặt. Ta đối chiếu
   luôn với "magic bytes" ở đầu file: PDF thật bắt đầu bằng ``%PDF-``, DOCX thật
   là một file ZIP nên bắt đầu bằng ``PK\\x03\\x04``. Đặt tên ``.pdf`` cho một
   file thực chất là thứ khác sẽ bị chặn ngay, trước khi nó tới tay pypdf.

2. **Lazy import.** ``pypdf`` và ``python-docx`` chỉ được import khi thật sự
   cần, đúng khuôn ``vehicle_classifier.py`` làm với torch. Nhờ vậy nhánh
   TXT/MD chạy được kể cả khi chưa cài hai gói đó, và test cắt đoạn không bị
   kéo theo cả một cây phụ thuộc.

3. **Rỗng là lỗi, không phải kết quả.** PDF scan tách ra chuỗi rỗng. Nếu cứ thế
   đi tiếp, ta sẽ ghi vào kho một tài liệu không có chữ nào rồi báo owner
   "đã nạp xong" — họ tin là quy chế đã vào hệ thống, trong khi Copilot không
   bao giờ tìm thấy gì. Thà báo lỗi rõ ràng.

[GOTCHA] Trần thời gian parse KHÔNG áp ở đây mà ở tầng service điều phối, vì
việc canh giờ thuộc về người biết cả lượt nạp kéo dài bao lâu. Xem
``DOCUMENT_PARSE_TIMEOUT_SECONDS`` trong ``app/core/constants.py``.
"""
import io
import os
from typing import List

from app.core.constants import KNOWLEDGE_MAX_FILE_BYTES
from app.core.enums import DocumentFormat
from app.core.exceptions import (
    DocumentTooLargeError,
    NoTextLayerError,
    UnsupportedFormatError,
)
from app.core.knowledge.dtos.knowledge_dto import ParsedDocument
from app.util.logger import logger

_THEO_DUOI_FILE = {
    ".pdf": DocumentFormat.PDF,
    ".docx": DocumentFormat.DOCX,
    ".txt": DocumentFormat.TXT,
    ".md": DocumentFormat.MARKDOWN,
    ".markdown": DocumentFormat.MARKDOWN,
}

# Chữ ký đầu file. TXT/MD không có chữ ký nào — văn bản thuần trông như bất cứ thứ gì.
_CHU_KY = {
    DocumentFormat.PDF: b"%PDF-",
    DocumentFormat.DOCX: b"PK\x03\x04",
}


def _doan_dinh_dang(file_name: str) -> DocumentFormat:
    duoi = os.path.splitext(file_name or "")[1].lower()
    dinh_dang = _THEO_DUOI_FILE.get(duoi)
    if dinh_dang is None:
        raise UnsupportedFormatError(
            f"Không đọc được định dạng '{duoi or 'không rõ'}'. "
            f"Chỉ nhận: PDF, DOCX, TXT, MD."
        )
    return dinh_dang


def _doi_chieu_chu_ky(file_data: bytes, dinh_dang: DocumentFormat) -> None:
    chu_ky = _CHU_KY.get(dinh_dang)
    if chu_ky and not file_data.startswith(chu_ky):
        raise UnsupportedFormatError(
            f"Nội dung file không khớp phần mở rộng: tên file khai là "
            f"{dinh_dang.value} nhưng dữ liệu bên trong không phải. "
            f"Vui lòng tải lên đúng file gốc."
        )


def _tach_pdf(file_data: bytes) -> ParsedDocument:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(file_data))
    canh_bao: List[str] = []

    if getattr(reader, "is_encrypted", False):
        # Một số PDF mã hoá rỗng mở được bằng mật khẩu trắng; thử một lần rồi thôi.
        try:
            reader.decrypt("")
        except Exception:
            raise UnsupportedFormatError(
                "File PDF được đặt mật khẩu nên không đọc được nội dung."
            )

    cac_trang: List[str] = []
    for so_trang, trang in enumerate(reader.pages, start=1):
        try:
            cac_trang.append(trang.extract_text() or "")
        except Exception as exc:
            # Một trang hỏng không nên giết cả tài liệu 200 trang.
            canh_bao.append(f"Trang {so_trang} không đọc được: {exc}")
            cac_trang.append("")

    return ParsedDocument(
        text="\n\n".join(p for p in cac_trang if p.strip()),
        doc_format=DocumentFormat.PDF,
        page_count=len(reader.pages),
        warnings=canh_bao,
    )


def _tach_docx(file_data: bytes) -> ParsedDocument:
    import docx

    tai_lieu = docx.Document(io.BytesIO(file_data))
    phan: List[str] = [p.text for p in tai_lieu.paragraphs if p.text.strip()]

    # Bảng biểu phí là thứ hay gặp nhất trong quy chế bãi xe, mà `paragraphs`
    # KHÔNG bao gồm nội dung trong bảng. Bỏ qua bảng là bỏ qua đúng phần đáng
    # giá nhất của tài liệu.
    for bang in tai_lieu.tables:
        for hang in bang.rows:
            o = [c.text.strip() for c in hang.cells if c.text.strip()]
            if o:
                phan.append(" | ".join(o))

    return ParsedDocument(
        text="\n\n".join(phan),
        doc_format=DocumentFormat.DOCX,
        page_count=None,
        warnings=[],
    )


def _tach_van_ban(file_data: bytes, dinh_dang: DocumentFormat) -> ParsedDocument:
    canh_bao: List[str] = []
    try:
        noi_dung = file_data.decode("utf-8")
    except UnicodeDecodeError:
        # Văn bản tiếng Việt xuất từ công cụ cũ hay là cp1258/latin-1. Giải mã
        # bỏ qua ký tự hỏng còn hơn từ chối cả file vì vài byte lạ.
        noi_dung = file_data.decode("utf-8", errors="replace")
        canh_bao.append("File không phải UTF-8 hợp lệ; một số ký tự có thể sai.")

    return ParsedDocument(
        text=noi_dung,
        doc_format=dinh_dang,
        page_count=None,
        warnings=canh_bao,
    )


def parse_document(file_data: bytes, file_name: str) -> ParsedDocument:
    """Tách text từ raw bytes. Ném lỗi có phân loại thay vì trả về rỗng.

    Raises:
        DocumentTooLargeError: vượt ``KNOWLEDGE_MAX_FILE_BYTES``.
        UnsupportedFormatError: đuôi lạ, nội dung không khớp đuôi, hoặc PDF khoá.
        NoTextLayerError: đọc được file nhưng không có chữ nào (bản scan).
    """
    if not file_data:
        raise NoTextLayerError("File rỗng.")

    if len(file_data) > KNOWLEDGE_MAX_FILE_BYTES:
        raise DocumentTooLargeError(
            f"File {len(file_data) / 1024 / 1024:.1f}MB vượt trần "
            f"{KNOWLEDGE_MAX_FILE_BYTES / 1024 / 1024:.0f}MB."
        )

    dinh_dang = _doan_dinh_dang(file_name)
    _doi_chieu_chu_ky(file_data, dinh_dang)

    if dinh_dang is DocumentFormat.PDF:
        ket_qua = _tach_pdf(file_data)
    elif dinh_dang is DocumentFormat.DOCX:
        ket_qua = _tach_docx(file_data)
    else:
        ket_qua = _tach_van_ban(file_data, dinh_dang)

    if not ket_qua.text.strip():
        raise NoTextLayerError(
            "Tài liệu không có lớp văn bản — nhiều khả năng đây là bản scan hoặc "
            "ảnh chụp. Vui lòng tải lên bản gốc số hoá."
        )

    logger.info(
        f"Đã tách tài liệu '{file_name}' ({dinh_dang.value}): "
        f"{len(ket_qua.text)} ký tự, {len(ket_qua.warnings)} cảnh báo"
    )
    return ket_qua
