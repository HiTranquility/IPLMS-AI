"""REST route ANPR — dùng cho upload ảnh thủ công / công cụ vận hành.
Đường nóng check-in/check-out của backend đi bằng gRPC (`VisionService`).
"""
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.api.rest.image_upload import read_image_upload
from app.core.constants import ANPR_MAX_FILES_PER_REQUEST
from app.core.vision import AnprItem, AnprService
from app.api.rest.schemas.base_response import BaseResponse
from app.util.logger import logger

router = APIRouter(prefix="/anpr", tags=["ANPR"])

AnprResponse = BaseResponse[AnprItem]


@router.post("/recognize", response_model=AnprResponse)
async def recognize(
    file: UploadFile = File(...),
    lane_id: Optional[str] = Query(None),
) -> AnprResponse:
    image_bytes = await read_image_upload(file)
    try:
        result = await AnprService.recognize(image_bytes, lane_id=lane_id)
    except Exception:
        # Chi tiết chỉ vào log: message exception có thể lộ đường dẫn/tên model (bug-043).
        logger.exception("ANPR REST recognize failed")
        return AnprResponse.fail("Recognition failed")
    return AnprResponse.ok([AnprItem.from_result(result)], "Recognized")


@router.post("/recognize-many", response_model=AnprResponse)
async def recognize_many(
    files: List[UploadFile] = File(...),
    lane_id: Optional[str] = Query(None),
) -> AnprResponse:
    if not files:
        return AnprResponse.fail("No files uploaded")
    if len(files) > ANPR_MAX_FILES_PER_REQUEST:
        raise HTTPException(413, f"Tối đa {ANPR_MAX_FILES_PER_REQUEST} ảnh mỗi request")

    # Kiểm hết ảnh trước khi chạy engine: ảnh hỏng ở cuối không làm phí CPU của các ảnh đầu.
    images = [await read_image_upload(file) for file in files]
    items: List[AnprItem] = []
    for image_bytes in images:
        try:
            result = await AnprService.recognize(image_bytes, lane_id=lane_id)
        except Exception:
            logger.exception("ANPR REST recognize-many item failed")
            continue
        items.append(AnprItem.from_result(result))

    if not items:
        return AnprResponse.fail(f"Recognized 0/{len(files)}")
    return AnprResponse.ok(items, f"Recognized {len(items)}/{len(files)}")
