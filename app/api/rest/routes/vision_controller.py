"""REST route cho Vision & Anti-Fraud Service."""
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile
from app.api.rest.developer_access import require_developer_access
from app.api.rest.image_upload import read_image_upload
from app.api.rest.schemas.base_response import BaseResponse
from app.api.rest.schemas.vision_schema import VerifyMatchRequest, VerifyMatchResponse
from app.core.vision import (
    AnprItem,
    AnprService,
    VehicleMatchQuery,
    VehicleMatchResult,
    anti_fraud_service,
)

router = APIRouter(prefix="/vision", tags=["Developer Vision"], dependencies=[Depends(require_developer_access)])


@router.post("/recognize", response_model=BaseResponse[AnprItem])
async def recognize_plate(
    file: UploadFile = File(...),
    lane_id: Optional[str] = Form(None),
) -> BaseResponse[AnprItem]:
    """Nhận diện biển số và phân loại loại xe từ ảnh gửi lên."""
    image_bytes = await read_image_upload(file)
    try:
        result = await AnprService.recognize(image_bytes, lane_id=lane_id)
        return BaseResponse.ok([AnprItem.from_result(result)], "Recognized")
    except Exception as exc:
        return BaseResponse.fail(f"Recognition failed: {exc}")


@router.post("/verify-match", response_model=BaseResponse[VerifyMatchResponse])
async def verify_vehicle_match(payload: VerifyMatchRequest) -> BaseResponse[VerifyMatchResponse]:
    """Đối chiếu loại xe check-in và check-out để phát hiện tráo xe."""
    try:
        query = VehicleMatchQuery(
            expected_vehicle_type=payload.expected_vehicle_type,
            current_vehicle_type=payload.current_vehicle_type,
            checkin_crop_url=payload.checkin_crop_url or "",
            checkout_crop_url=payload.checkout_crop_url or "",
        )
        result: VehicleMatchResult = anti_fraud_service.verify_vehicle_match(query)
        resp_data = VerifyMatchResponse(
            is_matched=result.is_matched,
            similarity_score=result.similarity_score,
            mismatch_reason=str(result.mismatch_reason.value if hasattr(result.mismatch_reason, "value") else result.mismatch_reason),
        )
        msg = "Vehicle match verified" if result.is_matched else f"Mismatch detected: {resp_data.mismatch_reason}"
        return BaseResponse.ok([resp_data], msg)
    except Exception as exc:
        return BaseResponse.fail(f"Verification failed: {exc}")
