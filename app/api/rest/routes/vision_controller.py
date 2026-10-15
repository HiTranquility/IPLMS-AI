"""REST route cho Vision & Anti-Fraud Service."""
from typing import Optional
from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from app.core.vision.dtos.vision_dto import AnprItem, VehicleMatchQuery, VehicleMatchResult
from app.core.vision.services.anpr_service import AnprService
from app.core.vision.services.anti_fraud_service import anti_fraud_service
from app.api.rest.schemas.base_response import BaseResponse

router = APIRouter(prefix="/vision", tags=["Vision & Anti-Fraud"])


class VerifyMatchRequest(BaseModel):
    expected_vehicle_type: str
    current_vehicle_type: str
    checkin_crop_url: Optional[str] = ""
    checkout_crop_url: Optional[str] = ""


class VerifyMatchResponse(BaseModel):
    is_matched: bool
    similarity_score: float
    mismatch_reason: str


@router.post("/recognize", response_model=BaseResponse[AnprItem])
async def recognize_plate(
    file: UploadFile = File(...),
    lane_id: Optional[str] = Form(None),
) -> BaseResponse[AnprItem]:
    """Nhận diện biển số và phân loại loại xe từ ảnh gửi lên."""
    try:
        result = await AnprService.recognize(file, lane_id=lane_id)
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
