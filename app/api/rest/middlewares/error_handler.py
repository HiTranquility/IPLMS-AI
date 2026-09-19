"""Global exception handler — chuyển AiServiceError thành JSON response chuẩn."""
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AiServiceError
from app.utils.logger import logger


async def ai_service_error_handler(request: Request, exc: AiServiceError) -> JSONResponse:
    """Catch mọi AiServiceError và trả về JSON envelope thống nhất."""
    logger.warning(f"AiServiceError on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "total": 0,
            "message": str(exc),
            "data": [],
        },
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch lỗi không lường trước — tránh leak stacktrace ra client."""
    logger.exception(f"Unhandled error on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "total": 0,
            "message": "Internal server error",
            "data": [],
        },
    )
