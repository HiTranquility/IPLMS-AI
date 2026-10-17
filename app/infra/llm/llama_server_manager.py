"""Quản lý tiến trình llama-server (CUDA) cho mô hình Qwen3.5-4B-GGUF."""
from __future__ import annotations

import atexit
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from app.config import get_config
from app.core.exceptions import RagPipelineError
from app.util.logger import logger


class LlamaServerManager:
    """Khởi động và quản lý tiến trình llama-server.exe chạy mô hình GGUF."""

    def __init__(self) -> None:
        self._process: Optional[subprocess.Popen] = None
        self._is_started: bool = False

    def is_server_alive(self, url: str | None = None) -> bool:
        """Kiểm tra llama-server có đang phản hồi tại /health hay không."""
        config = get_config().llm
        base = (url or config.local_llm_url).rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        health_url = f"{base}/health"
        try:
            req = urllib.request.Request(health_url, headers={"User-Agent": "IPLMS-AI"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                return resp.status in (200, 204)
        except Exception:
            return False

    def ensure_server_running(self) -> None:
        """Đảm bảo llama-server CUDA đã sẵn sàng phục vụ inference."""
        config = get_config().llm
        if self.is_server_alive():
            return

        bin_path = Path(config.local_llm_binary_path).resolve()
        if not bin_path.exists():
            linux_bin = bin_path.with_suffix("")
            if linux_bin.exists():
                bin_path = linux_bin
            else:
                raise RagPipelineError(
                    f"Không tìm thấy binary llama-server tại {bin_path}. "
                    "Vui lòng kiểm tra thư mục var/bin/llama."
                )

        model_path = Path(config.local_llm_model_path).resolve()
        if not model_path.exists():
            raise RagPipelineError(
                f"Không tìm thấy file trọng số GGUF tại {model_path}. "
                "Vui lòng đợi quá trình tải mô hình Qwen3.5-4B-Q4_K_M.gguf hoàn tất."
            )

        cmd = [
            str(bin_path),
            "-m", str(model_path),
            "--alias", "Qwen3.5-4B-Q4_K_M,qwen,default",
            "--host", config.local_llm_host,
            "--port", str(config.local_llm_port),
            "-c", str(config.local_llm_ctx_size),
            "-np", str(getattr(config, "local_llm_parallel_slots", 1)),
            "-t", str(config.local_llm_threads),
            "-ngl", str(config.local_llm_gpu_layers),
            "--reasoning-budget", "0",
            "--log-disable",
        ]

        logger.info(
            "Đang khởi động llama-server CUDA: model=%s port=%d ngl=%d",
            model_path.name,
            config.local_llm_port,
            config.local_llm_gpu_layers,
        )

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(bin_path.parent),
            )
            atexit.register(self.stop_server)
        except Exception as exc:
            raise RagPipelineError(f"Không thể khởi chạy llama-server: {exc}") from exc

        max_wait = 60.0
        start = time.time()
        while time.time() - start < max_wait:
            if self.is_server_alive():
                logger.info("llama-server CUDA đã sẵn sàng trên cổng %d", config.local_llm_port)
                self._is_started = True
                return
            if self._process.poll() is not None:
                raise RagPipelineError(
                    f"llama-server thoát sớm với mã lỗi {self._process.returncode}."
                )
            time.sleep(0.5)

        raise RagPipelineError("Quá thời gian chờ llama-server khởi động (60s).")

    def stop_server(self) -> None:
        if self._process and self._process.poll() is None:
            logger.info("Đang dừng tiến trình llama-server...")
            try:
                self._process.terminate()
                self._process.wait(timeout=3)
            except Exception:
                self._process.kill()
            self._process = None


llama_server_manager = LlamaServerManager()
