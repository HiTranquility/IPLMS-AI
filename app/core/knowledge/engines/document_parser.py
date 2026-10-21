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

3. **Rỗng là lỗi, không phải kết quả.** Trang PDF không có lớp chữ được OCR;
   nếu OCR vẫn không tìm được chữ thì từ chối nạp thay vì ghi tài liệu trống.

[GOTCHA] Trần thời gian parse KHÔNG áp ở đây mà ở tầng service điều phối, vì
việc canh giờ thuộc về người biết cả lượt nạp kéo dài bao lâu. Xem
``DOCUMENT_PARSE_TIMEOUT_SECONDS`` trong ``app/core/constants.py``.
"""
import io
import math
import multiprocessing
import os
from typing import Any, Callable, List, Tuple

from app.core.constants import KNOWLEDGE_MAX_FILE_BYTES, PDF_TEXT_TIMEOUT_SECONDS
from app.core.enums import DocumentFormat
from app.core.exceptions import (
    DocumentTooLargeError,
    NoTextLayerError,
    RagPipelineError,
    UnsupportedFormatError,
)
from app.core.knowledge.dtos.knowledge_dto import ParsedDocument
from app.infra.ocr.reader import get_easyocr_reader
from app.util.logger import logger

# Phải OCR xong trong DOCUMENT_PARSE_TIMEOUT_SECONDS kể cả lần đầu nạp model (bug-026).
_PDF_OCR_MAX_PAGES = 6
_PDF_OCR_MAX_PIXELS = 4_000_000
_PDF_OCR_SCALE = 1.5

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


def _child_entry(conn, target: Callable[..., Any], args: tuple) -> None:
    try:
        conn.send((True, target(*args)))
    except BaseException as exc:  # gửi lỗi về thay vì chết im lặng
        try:
            conn.send((False, exc))
        except Exception:
            conn.send((False, RagPipelineError(f"Lỗi khi đọc tài liệu: {exc}")))
    finally:
        conn.close()


def _run_isolated(target: Callable[..., Any], args: tuple, timeout: float) -> Any:
    """Chạy ``target`` trong process con và GIẾT nó nếu quá ``timeout``.

    ``asyncio.wait_for(to_thread(...))`` ở tầng service chỉ trả lỗi cho request;
    Python không giết được thread, nên một PDF độc làm pypdf treo sẽ giam thread
    đó mãi, đủ nhiều file thì cạn pool dùng chung của cả service (đã thử
    2026-10-09). Process thì giết được. ``spawn`` (không ``fork``) vì process cha
    có thread gRPC — fork từ process nhiều thread dễ deadlock.
    """
    ctx = multiprocessing.get_context("spawn")
    parent, child = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_child_entry, args=(child, target, args), daemon=True)
    proc.start()
    child.close()
    try:
        if not parent.poll(timeout):
            raise DocumentTooLargeError(
                "Tài liệu mất quá nhiều thời gian để đọc chữ. Vui lòng kiểm tra lại file."
            )
        try:
            ok, payload = parent.recv()
        except EOFError as exc:  # process con chết (vd hết RAM) trước khi kịp gửi
            raise UnsupportedFormatError("Không đọc được nội dung file PDF.") from exc
    finally:
        if proc.is_alive():
            proc.kill()
        proc.join(5)
        parent.close()
    if ok:
        return payload
    raise payload


def _pdf_text_layer(file_data: bytes) -> Tuple[List[str], List[int], List[str], int]:
    """Phần dùng pypdf (nơi có các CVE "PDF làm parser treo"): chạy trong process con.

    Trả (chữ từng trang, chỉ số trang cần OCR, cảnh báo, số trang).
    """
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(file_data))
    canh_bao: List[str] = []

    if getattr(reader, "is_encrypted", False):
        # Một số PDF mã hoá rỗng mở được bằng mật khẩu trắng; thử một lần rồi thôi.
        try:
            unlocked = reader.decrypt("")
            if not unlocked:
                raise ValueError("PDF vẫn được mã hoá")
        except Exception:
            raise UnsupportedFormatError(
                "File PDF được đặt mật khẩu nên không đọc được nội dung."
            )

    cac_trang: List[str] = []
    can_ocr: List[int] = []
    for so_trang, trang in enumerate(reader.pages, start=1):
        try:
            noi_dung = trang.extract_text() or ""
            cac_trang.append(noi_dung)
            if len(noi_dung.strip()) < 25:
                can_ocr.append(so_trang - 1)
        except Exception as exc:
            # Một trang hỏng không nên giết cả tài liệu 200 trang.
            canh_bao.append(f"Trang {so_trang} không đọc được: {exc}")
            cac_trang.append("")
            can_ocr.append(so_trang - 1)
    return cac_trang, can_ocr, canh_bao, len(reader.pages)


def _tach_pdf(file_data: bytes) -> ParsedDocument:
    cac_trang, can_ocr, canh_bao, so_trang = _run_isolated(
        _pdf_text_layer, (file_data,), PDF_TEXT_TIMEOUT_SECONDS
    )
    if can_ocr:
        if len(can_ocr) > _PDF_OCR_MAX_PAGES:
            raise UnsupportedFormatError(
                f"PDF có {len(can_ocr)} trang cần OCR, vượt giới hạn "
                f"{_PDF_OCR_MAX_PAGES} trang mỗi lần nạp. Hãy chia tài liệu thành các file nhỏ hơn."
            )
        for index, noi_dung in _ocr_pdf_pages(file_data, can_ocr).items():
            if noi_dung:
                cac_trang[index] = "\n".join(part for part in (cac_trang[index], noi_dung) if part.strip())
                canh_bao.append(f"Trang {index + 1} được nhận dạng chữ từ ảnh; hãy kiểm tra lại nội dung.")

    return ParsedDocument(
        text="\n\n".join(p for p in cac_trang if p.strip()),
        doc_format=DocumentFormat.PDF,
        page_count=so_trang,
        warnings=canh_bao,
    )


def _ocr_pdf_pages(file_data: bytes, page_indices: List[int]) -> dict[int, str]:
    import numpy as np
    import pypdfium2 as pdfium

    try:
        ocr = get_easyocr_reader()
    except Exception as exc:
        raise RagPipelineError("OCR chưa sẵn sàng để đọc PDF scan. Vui lòng thử lại sau.") from exc

    try:
        document = pdfium.PdfDocument(file_data)
    except Exception as exc:
        raise UnsupportedFormatError("Không dựng được trang PDF scan để nhận dạng chữ.") from exc
    results: dict[int, str] = {}
    try:
        for index in page_indices:
            page = document[index]
            try:
                width, height = page.get_size()
                if width <= 0 or height <= 0:
                    raise UnsupportedFormatError(f"Trang PDF {index + 1} có kích thước không hợp lệ.")
                scale = min(_PDF_OCR_SCALE, math.sqrt(_PDF_OCR_MAX_PIXELS / (width * height)))
                if scale < 0.75:
                    raise UnsupportedFormatError(
                        f"Trang PDF {index + 1} quá lớn để OCR an toàn. Hãy xuất lại trang ở kích thước nhỏ hơn."
                    )
                try:
                    bitmap = page.render(scale=scale)
                except Exception as exc:
                    raise UnsupportedFormatError(
                        f"Không dựng được trang PDF {index + 1} để OCR."
                    ) from exc
                try:
                    image = bitmap.to_pil()
                    try:
                        rgb = image.convert("RGB")
                        try:
                            try:
                                lines = ocr.readtext(np.array(rgb), detail=0, paragraph=True)
                            except Exception as exc:
                                raise RagPipelineError(
                                    f"OCR lỗi khi đọc trang PDF {index + 1}. Vui lòng thử lại sau."
                                ) from exc
                        finally:
                            rgb.close()
                    finally:
                        image.close()
                finally:
                    bitmap.close()
                results[index] = "\n".join(str(line).strip() for line in lines if str(line).strip())
            finally:
                page.close()
    finally:
        document.close()
    return results


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
        NoTextLayerError: PDF đã OCR hoặc file khác nhưng vẫn không có chữ nào.
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
            "Tài liệu không có chữ đọc được, kể cả sau khi nhận dạng PDF scan. "
            "Vui lòng tải lên bản rõ nét hơn."
        )

    logger.info(
        f"Đã tách tài liệu '{file_name}' ({dinh_dang.value}): "
        f"{len(ket_qua.text)} ký tự, {len(ket_qua.warnings)} cảnh báo"
    )
    return ket_qua
