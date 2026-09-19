"""CORS configuration cho FastAPI."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def register_cors(app: FastAPI) -> None:
    """Gắn CORS middleware vào FastAPI app.

    Mặc định cho phép mọi origin trong dev — production nên thu hẹp
    ``allow_origins`` qua config hoặc env var.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
