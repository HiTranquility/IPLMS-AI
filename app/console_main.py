"""FastAPI riêng của AI Console — process tách khỏi inference, chỉ dùng nội bộ (ADR-0048).

Chạy native: `python -m app.console_main` (nghe AI_CONSOLE_BIND_HOST, mặc định 127.0.0.1).
[NEVER] mount vào `app/main.py`: tải của người dùng console không được chạm inference cổng.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.rest.console_router import console_router
from app.api.rest.middlewares.error_handler import ai_service_error_handler, generic_error_handler
from app.config import get_config
from app.core.exceptions import AiServiceError, ConsoleAccessDenied, ConsoleAuthError
from app.util.console import enable_utf8_stdio

enable_utf8_stdio()

# Không bật docs: Swagger UI tải script từ CDN, trái luật 0 CDN của console.
app = FastAPI(title="IPLMS AI Console", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None)


def _error(status: int, message: str, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"success": False, "total": 0, "message": message, "data": [], "code": code},
    )


@app.exception_handler(ConsoleAuthError)
async def _auth_error(_: Request, exc: ConsoleAuthError) -> JSONResponse:
    return _error(401, str(exc), exc.code)


@app.exception_handler(ConsoleAccessDenied)
async def _access_denied(_: Request, exc: ConsoleAccessDenied) -> JSONResponse:
    return _error(403, str(exc), "FORBIDDEN")


@app.exception_handler(ValueError)
async def _invalid(_: Request, exc: ValueError) -> JSONResponse:
    return _error(400, str(exc), "INVALID_INPUT")


app.add_exception_handler(AiServiceError, ai_service_error_handler)
app.add_exception_handler(Exception, generic_error_handler)


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/console/api/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}


app.include_router(console_router, prefix="/console/api")


if __name__ == "__main__":
    import uvicorn

    cfg = get_config().console
    uvicorn.run(app, host=cfg.bind_host, port=cfg.port)
