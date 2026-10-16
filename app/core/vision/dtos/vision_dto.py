"""DTO Domain Vision — ANPR, phân loại xe và đối chiếu chống tráo xe."""
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel

from app.core.enums import FraudReason


@dataclass
class PlateResult:
    """Kết quả 1 lần nhận diện (model nội bộ của domain, stateless)."""

    plate_number: str
    crop_image_url: str
    event_id: str
    timestamp: str
    lane_id: Optional[str] = None
    original_image_url: Optional[str] = None
    vehicle_type: Optional[str] = None
    confidence: Optional[float] = None
    process_time: Optional[float] = None
    # Ảnh crop dạng bytes để backend đẩy lên kho lưu trữ bền. Không dùng cho
    # đường REST (đường đó đã ghi file và trả URL).
    crop_bytes: Optional[bytes] = None
    plate_color: Optional[str] = None


class AnprItem(BaseModel):
    """1 phần tử trong payload REST `/api/anpr/*` — hợp đồng với `AnprProvider`."""

    event_id: str
    lane_id: Optional[str] = None
    plate_number: str
    confidence: Optional[float] = None
    vehicle_type: Optional[str] = None
    crop_plate_image_url: str
    original_image_url: Optional[str] = None
    process_time: Optional[float] = None
    timestamp: str
    plate_color: Optional[str] = None

    @classmethod
    def from_result(cls, result: PlateResult) -> "AnprItem":
        return cls(
            event_id=result.event_id,
            lane_id=result.lane_id,
            plate_number=result.plate_number,
            confidence=result.confidence,
            vehicle_type=result.vehicle_type,
            crop_plate_image_url=result.crop_image_url,
            original_image_url=result.original_image_url,
            process_time=result.process_time,
            timestamp=result.timestamp,
            plate_color=result.plate_color,
        )


class RecognizePlateCommand(BaseModel):
    """Đầu vào 1 lượt nhận diện, đã tách khỏi message protobuf."""

    image_data: bytes
    lane_id: Optional[str] = None
    classify_vehicle: bool = True


class VehicleMatchQuery(BaseModel):
    """Đầu vào 1 lượt đối chiếu chống tráo xe."""

    checkin_crop_url: str
    checkout_crop_url: str
    expected_vehicle_type: str
    current_vehicle_type: str


class VehicleMatchResult(BaseModel):
    """Kết luận đối chiếu xe giữa check-in và check-out."""

    is_matched: bool
    similarity_score: float
    mismatch_reason: FraudReason
