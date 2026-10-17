"""DTO Domain Knowledge — nạp tài liệu quy chế bãi xe vào kho tri thức RAG."""
from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.core.enums import DocumentFormat, IngestStatus


class IngestDocumentCommand(BaseModel):
    """Đầu vào 1 lượt nạp, đã tách khỏi message protobuf."""

    file_data: bytes
    file_name: str

    # RỖNG/None = quy chế toàn hệ thống, mọi bãi tra được.
    # Có giá trị = chỉ bãi đó thấy (Rule 1 — cách ly theo bãi, SUGGESTION-008 §2.2).
    parking_lot_id: Optional[str] = None

    category: str = "regulation"
    uploaded_by: Optional[str] = None

    # Caller-supplied idempotency key. Retrying the same upload with the same
    # UUID replaces its chunks transactionally instead of creating duplicates.
    document_id: Optional[UUID] = None


@dataclass
class TextChunk:
    """Một đoạn văn bản đã cắt, TRƯỚC khi có embedding.

    Tách khỏi ``KnowledgeChunk`` có chủ đích: kiểu này là thứ ``chunker`` trả ra
    và còn thuần tuý — không phụ thuộc API embedding nào. Nhờ vậy test cắt đoạn
    chạy được mà không cần network, không cần API key.
    """

    content: str
    # Thứ tự trong tài liệu gốc, giữ để truy vết và để ghép lại ngữ cảnh sau này.
    ordinal: int
    # Tiêu đề điều khoản chứa đoạn này, nếu nhận ra được ("Điều 5 - Quy trình…").
    # None khi cắt theo ngưỡng ký tự chứ không theo cấu trúc.
    section_title: Optional[str] = None


@dataclass
class KnowledgeChunk:
    """Một đoạn ĐÃ có embedding, sẵn sàng ghi xuống pgvector."""

    content: str
    embedding: List[float]
    ordinal: int
    category: str
    source: str
    parking_lot_id: Optional[str] = None
    section_title: Optional[str] = None


@dataclass
class IngestResult:
    """Kết quả 1 lượt nạp.

    ``status`` phân biệt rõ "nạp được nhưng rỗng" với "hỏng" — owner cần biết
    chính xác vì sao tài liệu của họ không vào được, chứ không phải một chữ
    "thất bại" chung chung.
    """

    document_id: str
    status: IngestStatus
    chunk_count: int = 0
    message: str = ""
    process_time: float = 0.0
    # Bản NHÁP vừa ghi (ISSUE-009). Rỗng/0 khi status != SUCCESS.
    version_id: str = ""
    version_no: int = 0


@dataclass
class KnowledgeDocumentSummary:
    """1 dòng `knowledge_documents` — metadata tài liệu đã nạp, không kèm nội dung."""

    document_id: str
    file_name: str
    category: str
    uploaded_by: Optional[str]
    chunk_count: int
    created_at: str
    updated_at: str
    # Phiên bản mới nhất chưa lưu trữ + trạng thái của nó; 0/"" nếu chưa có.
    latest_version_no: int = 0
    latest_status: str = ""
    # Phiên bản khách đang thấy; 0 = khách chưa thấy tài liệu này.
    published_version_no: int = 0

    @property
    def duration_ms(self) -> float:
        return round(self.process_time * 1000.0, 2)


class KnowledgeDocumentItem(BaseModel):
    """1 phần tử trong payload REST `/api/knowledge/*` — hợp đồng với công cụ vận hành."""

    document_id: str
    file_name: str
    parking_lot_id: Optional[str] = None
    category: str
    status: str
    chunk_count: int = 0
    message: str = ""
    process_time: Optional[float] = None

    @classmethod
    def from_result(cls, result: IngestResult, command: IngestDocumentCommand) -> "KnowledgeDocumentItem":
        return cls(
            document_id=result.document_id,
            file_name=command.file_name,
            parking_lot_id=command.parking_lot_id,
            category=command.category,
            status=result.status.value,
            chunk_count=result.chunk_count,
            message=result.message,
            process_time=result.process_time,
        )


@dataclass
class ParsedDocument:
    """Kết quả tách text thô từ 1 file, trước khi cắt đoạn."""

    text: str
    doc_format: DocumentFormat
    # Số trang với PDF/DOCX; None với TXT/MD (không có khái niệm trang).
    page_count: Optional[int] = None
    warnings: List[str] = field(default_factory=list)
