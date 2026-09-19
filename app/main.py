"""FastAPI entrypoint for the IPLMS AI service."""
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.rest.router import api_router
from app.api.rest.middlewares.cors import register_cors
from app.api.rest.middlewares.error_handler import ai_service_error_handler, generic_error_handler
from app.core.exceptions import AiServiceError
from app.utils.console import enable_utf8_stdio

enable_utf8_stdio()

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
os.makedirs(os.path.join(STATIC_DIR, "cropped"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "original"), exist_ok=True)

app = FastAPI(title="IPLMS AI — Microservice API", version="0.3.0")
register_cors(app)
app.add_exception_handler(AiServiceError, ai_service_error_handler)
app.add_exception_handler(Exception, generic_error_handler)
app.include_router(api_router, prefix="/api")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "iplms-ai"}
