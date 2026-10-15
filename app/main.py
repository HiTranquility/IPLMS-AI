"""FastAPI entrypoint for the IPLMS AI service."""
import os
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
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
    if not get_config().vision.vision_warmup_on_start:
        logger.info("Vision warm-up skipped; models will lazy-load on first ANPR request.")
    else:
        from app.core.vision.engines.anpr_engine import warmup

        if await asyncio.to_thread(warmup):
            logger.info("Vision model loaded — REST ANPR is ready.")
        else:
            logger.error("Vision OCR failed to load — REST ANPR is unavailable.")
    yield


app = FastAPI(title="IPLMS AI — Microservice API", version="0.3.0", lifespan=lifespan)
register_cors(app)
app.add_exception_handler(AiServiceError, ai_service_error_handler)
app.add_exception_handler(Exception, generic_error_handler)
from fastapi.responses import FileResponse, HTMLResponse

app.include_router(api_router, prefix="/api")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "iplms-ai"}

@app.get("/", include_in_schema=False)
@app.get("/dashboard", include_in_schema=False)
@app.get("/ui", include_in_schema=False)
def dashboard() -> FileResponse:
    index_file = os.path.join(STATIC_DIR, "index.html")
    return FileResponse(index_file)
