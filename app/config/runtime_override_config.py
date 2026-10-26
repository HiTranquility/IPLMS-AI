"""Cấu hình đổi tại trang Settings của AI Console, lưu ở var/runtime_settings.json.

Console ghi file; mọi process (console 8090, inference 8000) đọc lúc tạo AppConfig,
nên inference chỉ thấy giá trị mới sau khi khởi động lại.
"""
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Đường dẫn tuyệt đối theo gốc repo `ai/`, không phụ thuộc CWD. Test đổi qua env.
RUNTIME_SETTINGS_PATH = os.environ.get(
    "AI_RUNTIME_SETTINGS_PATH",
    str(Path(__file__).resolve().parents[2] / "var" / "runtime_settings.json"),
)

LOCAL_LLM_PROVIDERS = ("ollama", "local")


def _clamp(cast: Callable[[Any], Any], lo, hi) -> Callable[[Any], Any]:
    return lambda v: max(lo, min(hi, cast(v)))


# khoá file → (nhóm config, thuộc tính, ép kiểu + kẹp biên giống DTO ở console_tools_controller)
_FIELDS: dict[str, tuple[str, str, Callable[[Any], Any]]] = {
    "vision_device": ("vision", "device", lambda v: v if v in ("auto", "cuda", "cpu") else "auto"),
    "onnx_enabled": ("vision", "onnx_enabled", bool),
    "vision_warmup_on_start": ("vision", "vision_warmup_on_start", bool),
    "llm_provider": ("llm", "llm_provider", lambda v: v if v in LOCAL_LLM_PROVIDERS else None),
    "llm_model": ("llm", "llm_model", lambda v: str(v)[:128] or None),
    "local_llm_gpu_layers": ("llm", "local_llm_gpu_layers", _clamp(int, 0, 64)),
    "local_llm_ctx_size": ("llm", "local_llm_ctx_size", _clamp(int, 512, 32768)),
    "local_llm_threads": ("llm", "local_llm_threads", _clamp(int, 1, 64)),
    "local_llm_parallel_slots": ("llm", "local_llm_parallel_slots", _clamp(int, 1, 8)),
    "rag_min_similarity": ("llm", "rag_min_similarity", _clamp(float, 0.05, 0.95)),
    "rag_top_k": ("llm", "rag_top_k", _clamp(int, 1, 20)),
    "llm_timeout_seconds": ("llm", "llm_timeout_seconds", _clamp(float, 5.0, 300.0)),
    "llm_max_output_tokens": ("llm", "llm_max_output_tokens", _clamp(int, 128, 8192)),
    "vehicle_min_confidence": ("vision", "vehicle_min_confidence", _clamp(float, 0.1, 0.99)),
    "default_lane_id": ("vision", "lane_id", lambda v: str(v)[:64] or None),
    "telemetry_enabled": ("telemetry", "enabled", bool),
    "telemetry_retention_days": ("telemetry", "retention_days", _clamp(int, 1, 365)),
    "vision_retention_days": ("console", "vision_retention_days", _clamp(int, 1, 365)),
}


def apply_runtime_overrides(config) -> None:
    """Áp file override lên `config`. File hỏng thì bỏ cả file và log, không áp dở dang."""
    if not os.path.isfile(RUNTIME_SETTINGS_PATH):
        return
    try:
        with open(RUNTIME_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        parsed = []
        for key, (group, attr, cast) in _FIELDS.items():
            if key in data and data[key] is not None:
                value = cast(data[key])
                if value is not None:
                    parsed.append((group, attr, value))
    except Exception as exc:  # noqa: BLE001 — file hỏng không được chặn khởi động
        logger.warning("Bỏ qua %s vì không đọc được: %s", RUNTIME_SETTINGS_PATH, exc)
        return
    for group, attr, value in parsed:
        setattr(getattr(config, group), attr, value)


def snapshot_runtime_fields(config) -> dict[str, Any]:
    """Chụp giá trị hiện tại của các trường đổi được, để hoàn tác khi ghi file lỗi (A-53)."""
    return {(group, attr): getattr(getattr(config, group), attr) for group, attr, _ in _FIELDS.values()}


def restore_runtime_fields(config, snapshot: dict[str, Any]) -> None:
    for (group, attr), value in snapshot.items():
        setattr(getattr(config, group), attr, value)


def persist_runtime_overrides(overrides: dict[str, Any]) -> None:
    """Gộp `overrides` vào file. Lỗi ghi được ném ra để API không báo lưu giả."""
    unknown = set(overrides) - set(_FIELDS)
    if unknown:
        raise ValueError(f"Khoá cấu hình runtime không hỗ trợ: {sorted(unknown)}")
    os.makedirs(os.path.dirname(RUNTIME_SETTINGS_PATH), exist_ok=True)
    existing: dict[str, Any] = {}
    if os.path.isfile(RUNTIME_SETTINGS_PATH):
        with open(RUNTIME_SETTINGS_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f) or {}
    existing.update(overrides)
    # Ghi tệp tạm rồi thay, để process chết giữa chừng không để lại file hỏng.
    tmp_path = f"{RUNTIME_SETTINGS_PATH}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, RUNTIME_SETTINGS_PATH)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
