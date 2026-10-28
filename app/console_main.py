"""FastAPI riêng của AI Console — process tách khỏi inference, chỉ dùng nội bộ (ADR-0048).

Chạy native: `python -m app.console_main` (nghe AI_CONSOLE_BIND_HOST, mặc định 127.0.0.1).
[NEVER] mount vào `app/main.py`: tải của người dùng console không được chạm inference cổng.
"""
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from app.api.rest.console_router import console_router
from app.api.rest.middlewares.error_handler import ai_service_error_handler, generic_error_handler
from app.config import get_config
from app.core.exceptions import AiServiceError, ConsoleAccessDenied, ConsoleAuthError, ConsoleRateLimited
from app.util.console import enable_utf8_stdio

enable_utf8_stdio()

# Bản build của `ai/ui` (`pnpm --dir ui build`); compose mount thư mục này vào container.
UI_DIST = (Path(__file__).resolve().parent.parent / "ui" / "dist").resolve()
# Mọi script/style/ảnh chỉ từ chính console: 0 CDN (ADR-0048 §5).
_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'none'; "
    "form-action 'self'; object-src 'none'"
)

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


@app.exception_handler(ConsoleRateLimited)
async def _rate_limited(_: Request, exc: ConsoleRateLimited) -> JSONResponse:
    return _error(429, str(exc), "RATE_LIMITED")


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
    response.headers["Content-Security-Policy"] = _CSP
    return response


@app.get("/api/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}


app.include_router(console_router, prefix="/api")


@app.get("/api/{_path:path}", include_in_schema=False)
def api_not_found(_path: str) -> JSONResponse:
    # Đường API sai không được rơi xuống SPA và trả HTML 200.
    return _error(404, "Không có API này.", "NOT_FOUND")


@app.get("/assets/{path:path}", include_in_schema=False)
def assets(path: str):
    candidate = (UI_DIST / "assets" / path).resolve()
    if candidate.is_file() and candidate.is_relative_to(UI_DIST / "assets"):
        return FileResponse(candidate)
    return JSONResponse(status_code=404, content={"message": "Asset not found"})


# Không lộ swagger/openapi dù có fallback SPA (bug-014 / ADR-0048 §5).
@app.get("/docs", include_in_schema=False)
@app.get("/docs/{_path:path}", include_in_schema=False)
@app.get("/redoc", include_in_schema=False)
@app.get("/redoc/{_path:path}", include_in_schema=False)
@app.get("/openapi.json", include_in_schema=False)
def disabled_docs(_path: str = ""):
    return Response(status_code=404)


@app.get("/console", include_in_schema=False)
@app.get("/console/{_path:path}", include_in_schema=False)
def console_deprecated(_path: str = ""):
    # Bỏ hẳn đường /console (ISSUE-021), trả 404 không phục vụ SPA
    return Response(status_code=404)


@app.get("/", include_in_schema=False)
@app.get("/{path:path}", include_in_schema=False)
def ui(path: str = ""):
    """Phục vụ SPA: file tĩnh có thật thì trả file, còn lại trả index.html (route phía client)."""
    if not (UI_DIST / "index.html").is_file():
        return HTMLResponse(
            "<p>Chưa build giao diện console. Chạy <code>pnpm --dir ui install</code> "
            "rồi <code>pnpm --dir ui build</code> trong thư mục ai/.</p>",
            status_code=503,
        )
    if "/assets/" in f"/{path}":
        asset_sub = f"/{path}".split("/assets/", 1)[1]
        asset_candidate = (UI_DIST / "assets" / asset_sub).resolve()
        if asset_candidate.is_file() and asset_candidate.is_relative_to(UI_DIST / "assets"):
            return FileResponse(asset_candidate)
        return JSONResponse(status_code=404, content={"message": "Asset not found"})
    candidate = (UI_DIST / path).resolve()
    if path and candidate.is_file() and candidate.is_relative_to(UI_DIST):
        return FileResponse(candidate)
    return FileResponse(UI_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn

    cfg = get_config().console
    if cfg.reload:
        uvicorn.run("app.console_main:app", host=cfg.bind_host, port=cfg.port, reload=True)
    else:
        uvicorn.run(app, host=cfg.bind_host, port=cfg.port)
