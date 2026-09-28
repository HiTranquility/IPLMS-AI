"""Enum dùng chung cho AI service.

Ba enum dưới đây PHẢI khớp từng chữ với enum cùng tên trong `proto/*.proto`
(mapper dùng chính chuỗi này để tra giá trị protobuf). Đổi một bên mà quên bên
kia sẽ nổ ngay ở mapper chứ không lặng lẽ trả sai — đó là chủ đích.
"""
from enum import Enum


class VehicleType(str, Enum):
    """Loại phương tiện CNN phân loại.

    KHÔNG có trong proto: từ vựng loại xe thuộc bảng `parking.vehicle_types`
    bên backend, proto để `string` để không tạo nguồn sự thật thứ hai.
    """
    CAR_SEDAN = "car_sedan"
    CAR_SUV = "car_suv"
    MOTORBIKE = "motorbike"
    TRUCK = "truck"


class OccupancyStatus(str, Enum):
    """Mức tải bãi đỗ — khớp enum `OccupancyStatus` trong forecast_service.proto."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FraudReason(str, Enum):
    """Kết quả đối chiếu xe — khớp enum `MismatchReason` trong vision_service.proto."""
    OK = "OK"
    VEHICLE_TYPE_MISMATCH = "VEHICLE_TYPE_MISMATCH"
    PLATE_TAMPERING_SUSPECTED = "PLATE_TAMPERING_SUSPECTED"


class ArbitrationVerdict(str, Enum):
    """Phán quyết tranh chấp — khớp enum `ArbitrationVerdict` trong copilot_service.proto."""
    APPROVE_REFUND = "APPROVE_REFUND"
    REJECT = "REJECT"
    PARTIAL_REFUND = "PARTIAL_REFUND"


class DocumentFormat(str, Enum):
    """Định dạng tài liệu nạp được — khớp enum `DocumentFormat` trong knowledge_service.proto."""
    PDF = "PDF"
    DOCX = "DOCX"
    TXT = "TXT"
    MARKDOWN = "MARKDOWN"


class IngestStatus(str, Enum):
    """Kết quả 1 lượt nạp — khớp enum `IngestStatus` trong knowledge_service.proto.

    Bốn giá trị lỗi tách riêng thay vì một `FAILED` chung: mỗi loại ứng với một
    hành động khác nhau của owner — đổi file khác, dùng bản rõ nét hơn, hay chờ
    rồi thử lại. Gộp chúng lại là ném việc chẩn đoán sang cho người không có
    thông tin để chẩn đoán.
    """
    SUCCESS = "SUCCESS"
    NO_TEXT_LAYER = "NO_TEXT_LAYER"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    EMBEDDING_FAILED = "EMBEDDING_FAILED"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
