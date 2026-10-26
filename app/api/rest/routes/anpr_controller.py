"""REST route ANPR — dùng cho upload ảnh thủ công / công cụ vận hành.
Đường nóng check-in/check-out của backend đi bằng gRPC (`VisionService`).
"""
from typing import List, Optional

from fastapi import APIRouter, File, Query, UploadFile

from app.core.vision import AnprItem, AnprService
from app.api.rest.schemas.base_response import BaseResponse

router = APIRouter(prefix="/anpr", tags=["ANPR"])

AnprResponse = BaseResponse[AnprItem]


@router.post("/recognize", response_model=AnprResponse)
async def recognize(
    file: UploadFile = File(...),
    lane_id: Optional[str] = Query(None),
) -> AnprResponse:
    try:
        result = await AnprService.recognize(file, lane_id=lane_id)
    except Exception as exc:
        return AnprResponse.fail(f"Recognition failed: {exc}")
    return AnprResponse.ok([AnprItem.from_result(result)], "Recognized")


@router.post("/recognize-many", response_model=AnprResponse)
async def recognize_many(
    files: List[UploadFile] = File(...),
    lane_id: Optional[str] = Query(None),
) -> AnprResponse:
    if not files:
        return AnprResponse.fail("No files uploaded")

    items: List[AnprItem] = []
    for file in files:
        try:
            result = await AnprService.recognize(file, lane_id=lane_id)
        except Exception:
            continue
        items.append(AnprItem.from_result(result))

    if not items:
        return AnprResponse.fail(f"Recognized 0/{len(files)}")
    return AnprResponse.ok(items, f"Recognized {len(items)}/{len(files)}")
