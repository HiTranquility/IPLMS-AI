"""Module ghi nhật ký và tính toán chi phí, độ trễ cho mọi yêu cầu AI (Mục 4.2)."""
from __future__ import annotations

import json
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.util.logger import logger


class AiTelemetryLogger:
    """Ghi vết chi tiết từng yêu cầu AI (tokens, latency, prompt version, cost)."""

    def __init__(self, log_path: Optional[Path] = None, max_memory_entries: int = 1000) -> None:
        if log_path is None:
            self.log_file = Path(os.getcwd()) / "var" / "log" / "ai_requests.jsonl"
        else:
            self.log_file = log_path

        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._memory_buffer: deque[dict] = deque(maxlen=max_memory_entries)

    def record(
        self,
        endpoint: str,
        model: str,
        prompt_version: str,
        tools_called: List[str],
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        status: str = "SUCCESS",  # "SUCCESS", "REFUSED", "FALLBACK", "ERROR"
        cost_usd: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> dict:
        total_tokens = input_tokens + output_tokens

        # Tính chi phí: Mô hình Local (Qwen) = 0 USD; Mô hình Cloud = biểu phí OpenAI tiêu chuẩn
        if cost_usd is None:
            if "qwen" in model.lower() or "local" in model.lower():
                cost_usd = 0.0
            else:
                # Giá tham chiếu gpt-4o-mini: $0.15/1M input, $0.60/1M output
                cost_usd = round(
                    (input_tokens / 1_000_000) * 0.15 + (output_tokens / 1_000_000) * 0.60,
                    6,
                )

        entry = {
            "request_id": f"req-{uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint": endpoint,
            "model": model,
            "prompt_version": prompt_version,
            "tools_called": tools_called,
            "tokens": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": total_tokens,
            },
            "latency_ms": round(latency_ms, 2),
            "cost_usd": cost_usd,
            "status": status,
            "metadata": metadata or {},
        }

        with self._lock:
            self._memory_buffer.append(entry)
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception as exc:
                logger.warning("Không thể ghi log telemetry AI: %s", exc)

        return entry

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Tính toán các chỉ số trung bình theo yêu cầu mục 4.2 và dashboard mục 6.6."""
        with self._lock:
            entries = list(self._memory_buffer)

        total_reqs = len(entries)
        if total_reqs == 0:
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "refused_requests": 0,
                "fallback_requests": 0,
                "error_requests": 0,
                "avg_latency_ms": 0.0,
                "total_tokens": 0,
                "avg_tokens_per_request": 0.0,
                "total_cost_usd": 0.0,
                "avg_cost_usd_per_request": 0.0,
                "estimated_cloud_cost_saved_usd": 0.0,
                "active_model": "Qwen3.5-4B-Q4_K_M (Local CUDA)",
            }

        successes = sum(1 for e in entries if e["status"] == "SUCCESS")
        refusals = sum(1 for e in entries if e["status"] == "REFUSED")
        fallbacks = sum(1 for e in entries if e["status"] == "FALLBACK")
        errors = sum(1 for e in entries if e["status"] == "ERROR")

        total_lat = sum(e["latency_ms"] for e in entries)
        total_toks = sum(e["tokens"]["total_tokens"] for e in entries)
        total_cost = sum(e["cost_usd"] for e in entries)

        # Tính toán chi phí tiết kiệm được nếu chạy toàn bộ số token đó trên OpenAI GPT-4o
        cloud_equiv_cost = sum(
            (e["tokens"]["prompt_tokens"] / 1_000_000) * 2.50
            + (e["tokens"]["completion_tokens"] / 1_000_000) * 10.00
            for e in entries
        )
        saved_usd = max(0.0, cloud_equiv_cost - total_cost)

        return {
            "total_requests": total_reqs,
            "successful_requests": successes,
            "refused_requests": refusals,
            "fallback_requests": fallbacks,
            "error_requests": errors,
            "avg_latency_ms": round(total_lat / total_reqs, 1),
            "total_tokens": total_toks,
            "avg_tokens_per_request": round(total_toks / total_reqs, 1),
            "total_cost_usd": round(total_cost, 6),
            "avg_cost_usd_per_request": round(total_cost / total_reqs, 6),
            "estimated_cloud_cost_saved_usd": round(saved_usd, 4),
            "active_model": entries[-1].get("model", "Qwen3.5-4B-Q4_K_M"),
            "latest_prompt_version": entries[-1].get("prompt_version", "v2"),
        }


ai_telemetry_logger = AiTelemetryLogger()
