"""Quản lý tiến trình llama-server (CUDA) cho mô hình Qwen3.5-4B-GGUF."""
from __future__ import annotations

import atexit
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

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
        app_cfg = get_config()
        if hasattr(app_cfg, "reload_runtime_overrides"):
            app_cfg.reload_runtime_overrides()
        config = app_cfg.llm
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

    def _find_path(self, p_str: str) -> Path:
        p = Path(p_str)
        if p.is_absolute() and p.exists():
            return p
        candidates = [
            Path(os.getcwd()) / p,
            Path(__file__).resolve().parents[3] / p,
        ]
        for c in candidates:
            if c.exists():
                return c.resolve()
            if c.with_suffix("").exists():
                return c.with_suffix("").resolve()
        return p.resolve()

    def _resolve_model_path(self, config) -> Path:
        repo_root = Path(__file__).resolve().parents[3]
        model_name = getattr(config, "llm_model", "") or getattr(config, "active_model_name", "")
        if model_name:
            candidates = [
                repo_root / "model" / "checkpoint" / "llm" / model_name,
                repo_root / "model" / "checkpoint" / "llm" / f"{model_name}.gguf",
            ]
            for c in candidates:
                if c.exists() and c.is_file():
                    return c.resolve()
        return self._find_path(config.local_llm_model_path)

    def _start_server_process(self, config) -> None:
        bin_path = self._find_path(config.local_llm_binary_path)
        if not bin_path.exists():
            raise RagPipelineError(
                f"Không tìm thấy binary llama-server tại {bin_path}. "
                "Vui lòng kiểm tra thư mục var/bin/llama."
            )

        model_path = self._resolve_model_path(config)
        if not model_path.exists():
            raise RagPipelineError(
                f"Không tìm thấy file trọng số GGUF tại {model_path}. "
                "Vui lòng kiểm tra lại tên mô hình hoặc tải file GGUF về máy."
            )

        cmd = [
            str(bin_path),
            "-m", str(model_path),
            "--alias", f"{model_path.stem},qwen,default,qwen2.5:3b,qwen2.5:0.5b",
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
            "Đang khởi động llama-server CUDA: model=%s port=%d ngl=%d ctx=%d slots=%d",
            model_path.name,
            config.local_llm_port,
            config.local_llm_gpu_layers,
            config.local_llm_ctx_size,
            getattr(config, "local_llm_parallel_slots", 1),
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

    def ensure_server_running(self) -> None:
        """Đảm bảo llama-server CUDA đã sẵn sàng phục vụ inference."""
        app_cfg = get_config()
        if hasattr(app_cfg, "reload_runtime_overrides"):
            app_cfg.reload_runtime_overrides()
        config = app_cfg.llm
        if self.is_server_alive():
            return
        self._start_server_process(config)

    def kill_existing_server_processes(self) -> None:
        """Giải phóng triệt để các tiến trình llama-server còn sót trên hệ thống."""
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/IM", "llama-server.exe"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                subprocess.run(
                    ["pkill", "-9", "-f", "llama-server"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
        except Exception as exc:
            logger.warning("Không thể kill llama-server: %s", exc)

    def restart_server(self, cfg=None) -> dict[str, Any]:
        """Khởi động lại tiến trình llama-server CUDA với cấu hình mới nhất."""
        logger.info("Yêu cầu khởi động lại (Hot Reload) llama-server...")
        self.stop_server()
        self.kill_existing_server_processes()
        # Đợi 0.5s để hệ điều hành và driver giải phóng VRAM và port
        time.sleep(0.5)
        app_cfg = cfg or get_config()
        if hasattr(app_cfg, "reload_runtime_overrides"):
            app_cfg.reload_runtime_overrides()
        config = app_cfg.llm if hasattr(app_cfg, "llm") else app_cfg
        self._start_server_process(config)
        return {
            "status": "ok",
            "provider": "local",
            "model": getattr(config, "active_model_name", "local"),
            "port": config.local_llm_port,
            "gpu_layers": config.local_llm_gpu_layers,
            "ctx_size": config.local_llm_ctx_size,
            "threads": config.local_llm_threads,
            "parallel_slots": getattr(config, "local_llm_parallel_slots", 1),
        }

    def stop_server(self) -> None:
        if self._process and self._process.poll() is None:
            logger.info("Đang dừng tiến trình llama-server...")
            try:
                self._process.terminate()
                self._process.wait(timeout=3)
            except Exception:
                self._process.kill()
            self._process = None
        self._is_started = False


llama_server_manager = LlamaServerManager()
