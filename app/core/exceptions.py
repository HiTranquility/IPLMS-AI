"""Custom exception hierarchy cho AI service.

Quy ước:
- Tất cả exception nghiệp vụ kế thừa ``AiServiceError``.
- Các tầng bên ngoài (handler, controller) chỉ cần catch ``AiServiceError``
  để trả lỗi chuẩn cho client.
"""


class AiServiceError(Exception):
    """Lỗi gốc của mọi exception nghiệp vụ AI."""


# ── Chung ─────────────────────────────────────────────────────────────────────

class FeatureNotImplementedError(AiServiceError):
    """Endpoint đã khai trong proto nhưng phần nghiệp vụ phía sau chưa có thật.

    [MUST] Dùng cái này thay vì trả về dữ liệu bịa cho đủ hình dạng response.
    Một endpoint trả số liệu trông hợp lý sẽ được người dùng tin và hành động
    theo; nó nguy hiểm hơn hẳn một endpoint báo lỗi thẳng thắn, vì kiểu hỏng
    này không để lại dấu vết nào trong log lẫn trong metric.
    """


# ── Vision ────────────────────────────────────────────────────────────────────

class PlateRecognitionError(AiServiceError):
    """Không nhận diện được biển số từ ảnh đầu vào."""


class ModelNotLoadedError(AiServiceError):
    """Model AI (YOLO, CNN, …) chưa được load hoặc không tìm thấy checkpoint."""


class InvalidImageError(AiServiceError):
    """Ảnh đầu vào không hợp lệ (rỗng, decode thất bại, …)."""


# ── Anti-Fraud ────────────────────────────────────────────────────────────────

class FraudDetectedError(AiServiceError):
    """Phát hiện gian lận: loại xe hoặc ảnh không khớp giữa check-in/check-out."""


# ── Copilot ───────────────────────────────────────────────────────────────────

class RagPipelineError(AiServiceError):
    """Lỗi trong quá trình truy vấn RAG (embedding, LLM, pgvector)."""


# ── Knowledge / Nạp liệu ──────────────────────────────────────────────────────

class UnsupportedFormatError(AiServiceError):
    """Định dạng tài liệu không đọc được (ngoài PDF/DOCX/TXT/MD)."""


class NoTextLayerError(AiServiceError):
    """Tài liệu không có lớp văn bản — gần như chắc chắn là bản scan/ảnh chụp.

    Tách riêng khỏi ``UnsupportedFormatError`` vì hướng xử lý của owner khác hẳn:
    đây là file ĐÚNG định dạng nhưng cần bản gốc số hoá, không phải đổi định dạng.
    """


class DocumentTooLargeError(AiServiceError):
    """File vượt ``KNOWLEDGE_MAX_FILE_BYTES`` hoặc parse quá ``DOCUMENT_PARSE_TIMEOUT_SECONDS``."""


class EmbeddingError(AiServiceError):
    """Gọi API embedding thất bại.

    [MUST] Bên bắt lỗi này phải rollback cả lượt nạp. Ghi chunk với
    ``embedding = NULL`` biến nó thành rác vô hình: có trong bảng, đếm được,
    nhưng không truy vấn nào tìm ra. Đó đúng là lỗi đang tồn tại ở
    ``app/script/seed_regulations.py``.
    """
