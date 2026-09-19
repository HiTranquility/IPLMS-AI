"""Map message protobuf ↔ DTO Domain Vision. Handler không tự đụng field proto."""
from app.api.grpc.generated_stubs import get_stub
from app.core.vision.dtos.vision_dto import (
    PlateResult,
    RecognizePlateCommand,
    VehicleMatchQuery,
    VehicleMatchResult,
)

_pb2, _ = get_stub("vision_service")


def to_recognize_plate_command(message) -> RecognizePlateCommand:
    return RecognizePlateCommand(
        image_data=message.image_data,
        lane_id=message.lane_id or None,
        classify_vehicle=message.classify_vehicle,
    )


def to_vehicle_match_query(message) -> VehicleMatchQuery:
    return VehicleMatchQuery(
        checkin_crop_url=message.checkin_crop_url,
        checkout_crop_url=message.checkout_crop_url,
        expected_vehicle_type=message.expected_vehicle_type,
        current_vehicle_type=message.current_vehicle_type,
    )


def to_recognize_plate_response(result: PlateResult, process_time_ms: float):
    return _pb2.RecognizePlateResponse(
        event_id=result.event_id,
        plate_number=result.plate_number,
        confidence=float(result.confidence or 0.0),
        vehicle_type=result.vehicle_type or "",
        crop_image_url=result.crop_image_url,
        process_time_ms=process_time_ms,
        crop_image=result.crop_bytes or b"",
    )


def to_verify_vehicle_match_response(result: VehicleMatchResult):
    return _pb2.VerifyVehicleMatchResponse(
        is_matched=result.is_matched,
        similarity_score=result.similarity_score,
        # DTO giữ tên giá trị enum → tra thẳng sang protobuf. Sai chính tả là nổ
        # ngay tại đây thay vì lặng lẽ gửi 0 (UNSPECIFIED).
        mismatch_reason=_pb2.MismatchReason.Value(result.mismatch_reason),
    )
