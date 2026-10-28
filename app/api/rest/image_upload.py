"""Đọc ảnh upload ở biên REST: giới hạn byte và nhận dạng định dạng theo magic byte (bug-043)."""
from fastapi import HTTPException, UploadFile

from app.core.constants import ANPR_MAX_IMAGE_BYTES

# Chỉ tin magic byte; `content_type` do client tự khai.
_IMAGE_SIGNATURES = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")


async def read_image_upload(file: UploadFile, max_bytes: int = ANPR_MAX_IMAGE_BYTES) -> bytes:
    # Đọc tối đa max_bytes + 1: đủ để biết vượt trần mà không kéo cả file vào RAM.
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(413, f"Ảnh vượt {max_bytes // (1024 * 1024)}MB")
    if not data.startswith(_IMAGE_SIGNATURES):
        raise HTTPException(415, "Chỉ nhận ảnh JPEG hoặc PNG")
    return data
