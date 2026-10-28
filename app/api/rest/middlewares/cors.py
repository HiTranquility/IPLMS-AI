"""CORS configuration cho FastAPI."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_config


def register_cors(app: FastAPI) -> None:
    """Gắn CORS middleware theo danh sách ``AI_CORS_ALLOW_ORIGINS`` (bug-045).

    Danh sách rỗng thì không gắn middleware: không phát header CORS, trình duyệt
    chặn mọi trang khác origin đọc phản hồi. Không bật credentials vì REST
    inference không dùng cookie.
    """
    origins = get_config().server.cors_allow_origin_list
    if not origins:
        return
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
