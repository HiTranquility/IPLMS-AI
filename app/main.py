"""FastAPI entrypoint for the IPLMS AI service."""
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.rest.developer_access import require_developer_access
from app.api.rest.router import api_router
from app.api.rest.middlewares.cors import register_cors
from app.api.rest.middlewares.error_handler import ai_service_error_handler, generic_error_handler
from app.config import get_config
from app.core.exceptions import AiServiceError
from app.util.console import enable_utf8_stdio
from app.util.logger import logger

enable_utf8_stdio()

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
os.makedirs(os.path.join(STATIC_DIR, "cropped"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "original"), exist_ok=True)

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load vision dependencies before the REST service accepts ANPR traffic."""
    from app.core.vision.engines.anpr_engine import warmup

    if not get_config().vision.vision_warmup_on_start:
        # Dev: serve immediately, load in the background (bug-006).
        logger.info("Vision warm-up running in background; early ANPR requests wait for it.")
        asyncio.get_running_loop().run_in_executor(None, warmup)
    else:
        if await asyncio.to_thread(warmup):
            logger.info("Vision model loaded — REST ANPR is ready.")
        else:
            logger.error("Vision OCR failed to load — REST ANPR is unavailable.")
    yield


app = FastAPI(title="IPLMS AI — Microservice API", version="0.3.0", lifespan=lifespan)
register_cors(app)
app.add_exception_handler(AiServiceError, ai_service_error_handler)
app.add_exception_handler(Exception, generic_error_handler)
app.include_router(api_router, prefix="/api")
app.include_router(api_router)


class DiagnosticStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        if path.replace("\\", "/").split("/")[-1].lower() == "index.html":
            require_developer_access(Request(scope))
        return await super().get_response(path, scope)


app.mount("/static", DiagnosticStaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", include_in_schema=False)
@app.get("/dashboard", include_in_schema=False)
@app.get("/ui", include_in_schema=False)
def dashboard(_: None = Depends(require_developer_access)) -> FileResponse:
    index_file = os.path.join(STATIC_DIR, "index.html")
    return FileResponse(index_file, headers={
        "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store",
    })
