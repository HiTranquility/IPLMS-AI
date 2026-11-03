"""Công cụ thử trong AI Console: kiểm cấu hình, hỏi thử Copilot, nạp bản nháp tri thức, mô phỏng ML (IPLMS ADR-0050).

Chạy NGAY trong process console, gọi thẳng `app/core` — không đi qua REST/gRPC của
process inference (ADR-0048 §1). Không bao giờ trả giá trị secret/URL, chỉ "đã cấu
hình hay chưa".
"""
from __future__ import annotations

import asyncio
import importlib.metadata
import json
import os
from typing import Any, List, Optional
from uuid import UUID

from app.config import get_config
from app.config.runtime_override_config import (
    LOCAL_LLM_PROVIDERS,
    persist_runtime_overrides,
    restore_runtime_fields,
    snapshot_runtime_fields,
)
from app.core.console.dtos import ConsoleActor
from app.core.console.engines import access_policy
from app.core.constants import KNOWLEDGE_MAX_FILE_BYTES, SIMILARITY_NOT_MEASURED
from app.core.copilot import AskQuestionRequest, CopilotAnswer, copilot_service
from app.core.enums import IngestStatus
from app.core.forecast import _resolve_default_gold_lake_path, forecast_service
from app.core.knowledge.dtos.knowledge_dto import IngestDocumentCommand
from app.core.model_policy.engines.validation import TASKS as MODEL_TASKS
from app.core.vision import AnprService, RecognizePlateCommand, VehicleMatchQuery, anti_fraud_service
from app.infra.database.console_store import console_store
from app.util.logger import logger

CONSOLE_TRY_TASK = "console_try"
# Ảnh thử ANPR trên console: cùng trần với tệp tri thức, đủ cho ảnh camera cổng.
ANPR_TRY_MAX_BYTES = KNOWLEDGE_MAX_FILE_BYTES
_ALLOWED_SUFFIXES = (".pdf", ".docx", ".txt", ".md", ".markdown")


def _lot(parking_lot_id: Optional[str]) -> Optional[str]:
    value = (parking_lot_id or "").strip()
    if len(value) > 128:
        raise ValueError("Mã bãi tối đa 128 ký tự.")
    return value or None


def _engine_status(vision) -> dict[str, Any]:
    """Trạng thái engine Vision đọc từ cấu hình, đĩa và bộ nhớ process — không nạp model.

    Trường nào không biết chắc thì None để UI hiện "—" (ai bug-018: không hằng số).
    """
    path = vision.yolo_model_path
    loaded_yolo = loaded_ocr = None
    try:
        # Chỉ lazy-import adapter chứa trọng số nặng YOLO/EasyOCR để không ép nạp PyTorch khi khởi động.
        cfg = get_config()
        from app.core.vision.engines.anpr import model_loader as anpr_models

        loaded_yolo = anpr_models.yolo_model() is not None
        loaded_ocr = anpr_models.ocr_reader() is not None
    except Exception:  # noqa: BLE001 — thiếu thư viện vision thì báo "không rõ"
        pass
    cuda = False
    torch_version = None
    try:
        import torch
        torch_version = torch.__version__
        cuda = bool(torch.cuda.is_available())
    except Exception:
        try:
            torch_version = importlib.metadata.version("torch")
        except Exception:
            torch_version = None
        cuda = False
    return {
        "yolo_weights_path": path,
        "yolo_weights_bytes": os.path.getsize(path) if os.path.isfile(path) else None,
        "yolo_version": vision.yolo_model_version,
        "yolo_loaded": loaded_yolo,
        "ocr_languages": vision.ocr_language_list,
        "ocr_cache_dir": vision.ocr_model_storage_dir or None,
        "ocr_loaded": loaded_ocr,
        "onnx_enabled": vision.onnx_enabled,
        "torch_version": torch_version,
        "cuda_available": cuda,
    }


def _hardware_telemetry() -> dict[str, Any]:
    """Đo thông số phần cứng thật từ hệ điều hành & CUDA (không trả số hằng số giả — bug-018)."""
    import ctypes
    import subprocess

    cpu_cores = os.cpu_count()
    ram_total_mb: Optional[int] = None
    ram_avail_mb: Optional[int] = None
    ram_used_pct: Optional[float] = None

    try:
        if os.name == "nt":
            class _MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = _MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                ram_total_mb = int(stat.ullTotalPhys // (1024 * 1024))
                ram_avail_mb = int(stat.ullAvailPhys // (1024 * 1024))
                ram_used_pct = round(float(stat.dwMemoryLoad), 1)
        elif os.path.isfile("/proc/meminfo"):
            mem: dict[str, int] = {}
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        k = parts[0].strip()
                        v = parts[1].strip().split()[0]
                        if v.isdigit():
                            mem[k] = int(v)
            if "MemTotal" in mem and "MemAvailable" in mem:
                ram_total_mb = mem["MemTotal"] // 1024
                ram_avail_mb = mem["MemAvailable"] // 1024
                if ram_total_mb > 0:
                    ram_used_pct = round((ram_total_mb - ram_avail_mb) * 100.0 / ram_total_mb, 1)
    except Exception:
        pass

    cuda_available = False
    gpu_name: Optional[str] = None
    vram_total_mb: Optional[int] = None
    vram_used_mb: Optional[int] = None
    vram_free_mb: Optional[int] = None

    try:
        import torch
        if torch.cuda.is_available():
            cuda_available = True
            gpu_name = str(torch.cuda.get_device_name(0))
            free_b, total_b = torch.cuda.mem_get_info(0)
            vram_total_mb = int(total_b // (1024 * 1024))
            vram_free_mb = int(free_b // (1024 * 1024))
            vram_used_mb = max(0, vram_total_mb - vram_free_mb)
    except Exception as exc:  # noqa: BLE001 — không có torch/CUDA thì thử nvidia-smi
        logger.debug("Không đọc được GPU qua torch: %s", exc)

    if gpu_name is None:
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free", "--format=csv,noheader,nounits"],
                timeout=1.5,
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            if out:
                first = out.splitlines()[0].split(",")
                if len(first) >= 4:
                    cuda_available = True
                    gpu_name = first[0].strip()
                    vram_total_mb = int(float(first[1].strip()))
                    vram_used_mb = int(float(first[2].strip()))
                    vram_free_mb = int(float(first[3].strip()))
        except Exception:
            pass

    return {
        "cpu_logical_cores": cpu_cores,
        "ram_total_mb": ram_total_mb,
        "ram_available_mb": ram_avail_mb,
        "ram_used_percent": ram_used_pct,
        "cuda_available": cuda_available,
        "gpu_name": gpu_name,
        "vram_total_mb": vram_total_mb,
        "vram_used_mb": vram_used_mb,
        "vram_free_mb": vram_free_mb,
    }


def _detect_compute_profile(cfg) -> str:
    v_dev = (cfg.vision.device or "auto").lower()
    layers = int(getattr(cfg.llm, "local_llm_gpu_layers", 33))
    if v_dev == "cpu" and layers == 0:
        return "cpu_eco"
    if v_dev == "cpu" and layers >= 20:
        return "safe_4gb"
    if v_dev in ("cuda", "auto") and layers >= 20:
        return "gpu_full"
    return "custom"


def _ollama_api_bases(cfg) -> list[str]:
    """Danh sách gốc API Ollama ứng viên (tự dịch giữa 127.0.0.1 và host.docker.internal)."""
    raw_urls = [
        getattr(cfg.llm, "ollama_url", "") or "",
        getattr(cfg.llm, "llm_base_url", "") or "",
        "http://127.0.0.1:11434/v1",
    ]
    in_docker = os.path.exists("/.dockerenv")
    candidates: list[str] = []
    for raw in raw_urls:
        u = raw.strip().rstrip("/")
        if not u:
            continue
        if u.endswith("/v1"):
            u = u[:-3]
        variants = [u]
        if in_docker and ("127.0.0.1" in u or "localhost" in u):
            variants.insert(0, u.replace("127.0.0.1", "host.docker.internal").replace("localhost", "host.docker.internal"))
        elif not in_docker and "host.docker.internal" in u:
            variants.insert(0, u.replace("host.docker.internal", "127.0.0.1"))
        for v in variants:
            if v not in candidates:
                candidates.append(v)
    return candidates


def _reload_llm(cfg) -> dict[str, Any]:
    """Khởi động lại / nạp lại mô hình LLM theo cấu hình hiện thời."""
    prov = getattr(cfg.llm, "llm_provider", "local")
    if prov == "local":
        from app.infra.llm.llama_server_manager import llama_server_manager
        return llama_server_manager.restart_server(cfg)
    elif prov == "ollama":
        import urllib.request
        model_name = getattr(cfg.llm, "active_model_name", "qwen2.5:3b")
        layers = int(getattr(cfg.llm, "local_llm_gpu_layers", 33))
        num_gpu = 99 if layers >= 33 else max(0, layers)
        ctx_size = int(getattr(cfg.llm, "local_llm_ctx_size", 4096))
        threads = int(getattr(cfg.llm, "local_llm_threads", 4))
        req_data = json.dumps({
            "model": model_name,
            "prompt": "",
            "keep_alive": "10m",
            "options": {
                "num_gpu": num_gpu,
                "num_ctx": ctx_size,
                "num_thread": threads,
            },
        }).encode("utf-8")
        last_err: Optional[Exception] = None
        for api_base in _ollama_api_bases(cfg):
            generate_url = f"{api_base}/api/generate"
            req = urllib.request.Request(
                generate_url,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=15.0) as resp:
                    return {"status": "ok", "provider": "ollama", "model": model_name, "num_gpu": num_gpu}
            except Exception as e:
                last_err = e
        return {"status": "warning", "provider": "ollama", "model": model_name, "message": str(last_err or "")}
    return {"status": "noop", "provider": prov}


async def _effective_models() -> list[dict[str, Any]]:
    """Model inference dùng thật cho từng tác vụ (IPLMS ADR-0061 §2).

    Dựng `LlmFactory` giống `LlmFactory.for_task`: có revision ACTIVE thì theo revision,
    không có thì theo env. Không đọc được kho profile thì báo "unknown" chứ không đoán env.
    """
    from app.infra.database.model_policy_store import model_policy_store
    from app.infra.llm.llm_factory import LlmFactory

    rows: list[dict[str, Any]] = []
    for task in MODEL_TASKS:
        try:
            profile = await model_policy_store.get_active(task) if model_policy_store.db_url else None
        except Exception as exc:  # noqa: BLE001 — trang Settings vẫn mở được khi ai-db lỗi
            logger.warning("Không đọc được revision đang dùng cho %s: %s", task, exc)
            rows.append({"task": task, "provider": None, "model": None, "source": "unknown", "revision": None})
            continue
        llm = LlmFactory(profile=profile)
        rows.append({
            "task": task,
            "provider": llm.provider,
            "model": llm.model,
            "source": "profile" if profile else "env",
            "revision": profile["revision"] if profile else None,
        })
    return rows


class ToolsService:
    def __init__(self, store=None, copilot=None, ingestion=None) -> None:
        self.store = store or console_store
        self.copilot = copilot or copilot_service
        self._ingestion = ingestion

    def _ingestion_service(self):
        # Nạp trễ: parser PDF/DOCX + client embedding chỉ cần khi có người nạp.
        if self._ingestion is None:
            from app.core.knowledge import ingestion_service

            self._ingestion = ingestion_service
        return self._ingestion

    async def system_check(self, actor: ConsoleActor) -> dict:
        access_policy.require(actor, "ai:metrics:read")
        cfg = get_config()
        checks = [
            ("ai_database", "AI_DATABASE_URL (tri thức + telemetry)", bool(cfg.llm.database_url)),
            ("llm_key", "Khoá nhà cung cấp LLM", bool(cfg.llm.llm_api_key)),
            ("telemetry_hmac", "Khoá HMAC telemetry", bool(cfg.telemetry.hmac_key)),
            ("telemetry_price", "Giá token để tính chi phí",
             cfg.telemetry.price_input_per_mtok is not None and cfg.telemetry.price_output_per_mtok is not None),
            ("console_database", "AI_CONSOLE_DATABASE_URL", bool(cfg.console.database_url)),
            ("google_oidc", "Google OAuth client", bool(cfg.console.google_client_id and cfg.console.google_client_secret)),
            ("totp_key", "Khoá mã hoá TOTP", bool(cfg.console.totp_encryption_key)),
            ("cookie_secure", "Cookie chỉ qua HTTPS", cfg.console.cookie_secure),
        ]
        # Model Copilot inference dùng thật, không phải env khi đã có revision ACTIVE (ADR-0061 §2).
        copilot = next(m for m in await _effective_models() if m["task"] == "copilot_answer")
        return {
            "checks": [{"key": k, "label": label, "ok": bool(ok)} for k, label, ok in checks],
            "llm_model": copilot["model"] or "—",
            "telemetry_enabled": cfg.telemetry.enabled,
            "vision_device": getattr(cfg.vision, "resolved_device", cfg.vision.device),
            "telemetry_retention_days": cfg.telemetry.retention_days,
            "vision_retention_days": cfg.console.vision_retention_days,
            "engines": await asyncio.to_thread(_engine_status, cfg.vision),
        }

    async def try_anpr(self, actor: ConsoleActor, image: bytes, lane_id: Optional[str] = None) -> dict:
        """Chạy đúng engine ANPR đang nạp trong process này trên một ảnh (ai bug-018).

        Không lưu ảnh (persist_files=False): ảnh biển số là PII, lượt thử không để lại file.
        """
        access_policy.require(actor, "ai:model:evaluate")
        if not image:
            raise ValueError("Ảnh rỗng.")
        if len(image) > ANPR_TRY_MAX_BYTES:
            raise ValueError("Ảnh vượt 8 MB.")

        command = RecognizePlateCommand(image_data=image, lane_id=_lot(lane_id))
        result = await asyncio.to_thread(AnprService.recognize_bytes, command, False)

        crop_image_b64 = None
        crop_bytes = getattr(result, "crop_bytes", None)
        if crop_bytes:
            import base64
            crop_image_b64 = f"data:image/jpeg;base64,{base64.b64encode(crop_bytes).decode('ascii')}"

        return {
            "plate_number": result.plate_number,
            "confidence": result.confidence,
            "vehicle_type": result.vehicle_type,
            "plate_color": result.plate_color,
            "latency_ms": round(result.process_time * 1000, 1) if result.process_time is not None else None,
            "crop_image": crop_image_b64,
        }

    async def try_anpr_clip(self, actor: ConsoleActor, clip: bytes, content_type: str, motion: bool = False) -> dict:
        """Đọc biển số từ clip bằng engine ANPR đang nạp (IPLMS REQ-021 A).

        Clip không được lưu (F7); mỗi sự kiện chỉ mang ảnh cắt biển của frame tốt nhất.
        """
        access_policy.require(actor, "ai:model:evaluate")
        result = await asyncio.to_thread(AnprService.recognize_clip, clip, content_type, motion)
        import base64
        for event in result["events"]:
            crop = event.pop("crop_bytes", None)
            event["crop_image"] = (
                f"data:image/jpeg;base64,{base64.b64encode(crop).decode('ascii')}" if crop else None
            )
        return result

    async def verify_match(self, actor: ConsoleActor, expected_type: str, current_type: str) -> dict:
        """Đối chiếu loại xe vào/ra bằng anti_fraud_service thật (ai bug-018).

        Service chưa so ảnh (SUGGESTION-007 B6) nên `similarity_score` luôn là None ở đây,
        không trả hằng số 0.0 của service như thể đó là số đo.
        """
        access_policy.require(actor, "ai:model:evaluate")

        result = anti_fraud_service.verify_vehicle_match(VehicleMatchQuery(
            checkin_crop_url="", checkout_crop_url="",
            expected_vehicle_type=expected_type.strip(), current_vehicle_type=current_type.strip(),
        ))
        reason = getattr(result.mismatch_reason, "value", result.mismatch_reason)
        measured = result.similarity_score != SIMILARITY_NOT_MEASURED
        return {
            "is_matched": result.is_matched,
            "similarity_score": result.similarity_score if measured else None,
            "mismatch_reason": str(reason or ""),
        }

    async def knowledge_documents(self, actor: ConsoleActor, parking_lot_id: Optional[str] = None) -> list[dict]:
        """Tài liệu thật trong kho tri thức (metadata, không kèm nội dung) — ai bug-018."""
        access_policy.require(actor, "ai:prompt:edit")
        docs = await self._ingestion_service().list(_lot(parking_lot_id))
        return [
            {
                "id": d.document_id,
                "title": d.file_name,
                "category": d.category,
                "source": d.file_name,
                "chunk_count": d.chunk_count,
                "latest_version_no": d.latest_version_no,
                "latest_status": d.latest_status,
                "published_version_no": d.published_version_no,
                "updated_at": d.updated_at,
            }
            for d in docs
        ]

    async def delete_knowledge_document(
        self, actor: ConsoleActor, document_id: str, parking_lot_id: Optional[str] = None
    ) -> int:
        access_policy.require(actor, "ai:prompt:edit")
        deleted = await self._ingestion_service().delete(document_id, _lot(parking_lot_id))
        await self.store.add_audit(
            actor.member_id, "knowledge.delete", "knowledge_document",
            str(document_id), f"Đã xóa tài liệu {document_id}",
        )
        return deleted

    async def document_chunks(
        self, actor: ConsoleActor, document_id: str, parking_lot_id: Optional[str] = None, version_no: int = 0
    ) -> dict:
        access_policy.require(actor, "ai:prompt:edit")
        return await self._ingestion_service().vector_store.list_document_chunks(
            document_id, _lot(parking_lot_id), version_no
        )

    async def try_copilot_stream(
        self, actor: ConsoleActor, query: str, parking_lot_id: Optional[str] = None,
        top_k: Optional[int] = None, min_similarity: Optional[float] = None,
        temperature: Optional[float] = None, history: Optional[List[dict]] = None,
    ):
        # Tham số thử chỉ dùng được với quyền sửa prompt, cùng quyền của cả lượt thử.
        access_policy.require(actor, "ai:prompt:edit")
        query = (query or "").strip()
        if not 1 <= len(query) <= 2000:
            raise ValueError("Câu hỏi cần 1–2000 ký tự.")
        request = AskQuestionRequest(
            query=query, user_id=actor.member_id, user_role="console",
            parking_lot_id=_lot(parking_lot_id), preview=True,
            top_k=top_k, min_similarity=min_similarity, temperature=temperature,
            history=history,
        )
        async for chunk in self.copilot.stream_answer(request):
            yield chunk

    async def try_copilot(
        self, actor: ConsoleActor, query: str, parking_lot_id: Optional[str] = None,
        top_k: Optional[int] = None, min_similarity: Optional[float] = None,
        temperature: Optional[float] = None, history: Optional[List[dict]] = None,
    ) -> CopilotAnswer:
        access_policy.require(actor, "ai:prompt:edit")
        query = (query or "").strip()
        if not 1 <= len(query) <= 2000:
            raise ValueError("Câu hỏi cần 1–2000 ký tự.")
        request = AskQuestionRequest(
            query=query, user_id=actor.member_id, user_role="console",
            parking_lot_id=_lot(parking_lot_id), preview=True,
            top_k=top_k, min_similarity=min_similarity, temperature=temperature,
            history=history,
        )
        return await self.copilot.ask_question(request, task=CONSOLE_TRY_TASK)

    async def ingest_draft(
        self, actor: ConsoleActor, document_id: str, file_name: str, data: bytes,
        category: str = "regulation", parking_lot_id: Optional[str] = None,
    ) -> dict:
        access_policy.require(actor, "ai:prompt:edit")
        try:
            doc_uuid = UUID(document_id)
        except (ValueError, TypeError):
            raise ValueError("Mã tài liệu phải là UUID (giữ nguyên khi thử lại).") from None
        name = (file_name or "").strip()
        if not name.lower().endswith(_ALLOWED_SUFFIXES):
            raise ValueError("Chỉ nhận PDF, DOCX, TXT hoặc MD.")
        if not data:
            raise ValueError("Tệp rỗng.")
        if len(data) > KNOWLEDGE_MAX_FILE_BYTES:
            raise ValueError("Tệp vượt 8 MB.")
        category = (category or "regulation").strip()[:128] or "regulation"
        result = await self._ingestion_service().ingest(IngestDocumentCommand(
            file_name=name, file_data=data, category=category,
            parking_lot_id=_lot(parking_lot_id), document_id=doc_uuid, uploaded_by=actor.member_id,
        ))
        await self.store.add_audit(
            actor.member_id, f"knowledge.ingest_draft:{result.status.value}", "knowledge_document",
            str(result.document_id), f"{name} → bản nháp v{result.version_no}",
        )
        return {
            "document_id": str(result.document_id),
            "status": result.status.value,
            "ok": result.status == IngestStatus.SUCCESS,
            "chunk_count": result.chunk_count,
            "duration_ms": round(result.process_time * 1000, 1),
            "message": result.message,
            "version_id": result.version_id,
            "version_no": result.version_no,
        }

    async def list_forecast_areas(self, actor: ConsoleActor) -> dict:
        """Bãi có dữ liệu trong Gold lake để Simulator chọn đúng `area_key` (ai bug-028)."""
        access_policy.require(actor, "ai:metrics:read")
        areas = await asyncio.to_thread(forecast_service.list_lake_areas)
        return {"source_path": str(_resolve_default_gold_lake_path()), "areas": areas}

    async def simulate_forecast(
        self,
        actor: ConsoleActor,
        area_id: str = "AREA_CENTRAL_01",
        day_of_week: int = 4,
        total_capacity: int = 350,
        base_hourly_rate: float = 25000.0,
    ) -> dict:
        """Thực thi Pipeline 3 Machine Learning (Lakehouse Parquet -> LightGBM/Prophet Feature Matrix -> Surge Tariff)."""
        access_policy.require(actor, "ai:metrics:read")

        # Nạp lại theo đúng bãi: dataset cache của bãi khác làm sai cờ is_fallback (A-58).
        training_data = forecast_service.load_lakehouse_dataset(area_id=area_id, force_reload=True)
        weekly_profile = training_data.get("weekly_profile", {})
        lgbm = training_data.get("lightgbm_dataset", {})
        X_matrix = lgbm.get("features", [])
        y_vector = lgbm.get("targets", [])
        feature_names = lgbm.get(
            "feature_names",
            [
                "day_of_week", "hour_of_day", "is_weekend", "total_slots",
                "hour_sin", "hour_cos", "dow_sin", "dow_cos",
            ],
        )
        prophet_rows = training_data.get("prophet_dataset", [])

        target_hours = {8, 12, 18, 21}
        sample_rows = []
        for feat, target in zip(X_matrix, y_vector):
            if int(feat[0]) == day_of_week and int(feat[1]) in target_hours:
                sample_rows.append({
                    "day_of_week": int(feat[0]),
                    "hour_of_day": int(feat[1]),
                    "is_weekend": int(feat[2]),
                    "total_slots": int(feat[3]),
                    "hour_sin": feat[4],
                    "hour_cos": feat[5],
                    "dow_sin": feat[6],
                    "dow_cos": feat[7],
                    "occupancy_pct": target,
                })

        hourly_predictions = []
        peak_hour = 0
        peak_occ = 0.0
        is_fallback = bool(training_data.get("is_fallback", False))
        for h in range(24):
            detail = forecast_service.get_projected_occupancy_ratio_detail(area_id, day_of_week, h)
            occ = float(detail["ratio"])
            is_fallback = is_fallback or bool(detail["is_fallback"])
            mult, _ = forecast_service.calculate_surge_multiplier(occ)
            if occ > peak_occ:
                peak_occ = occ
                peak_hour = h
            hourly_predictions.append({
                "hour_of_day": h,
                "predicted_occupancy_pct": occ,
                "estimated_free_spots": max(0, int(round(total_capacity * (100.0 - occ) / 100.0))),
                "surge_multiplier": mult,
                "confidence": detail["confidence"],
            })

        rec_mult, rec_reason = forecast_service.calculate_surge_multiplier(peak_occ)
        effective_rate = round(base_hourly_rate * rec_mult, 2)

        return {
            "stage1_datalake": {
                "source_path": str(_resolve_default_gold_lake_path()),
                "is_fallback": is_fallback,
                "total_records": int(training_data.get("total_records", 0)),
                "area_ids": training_data.get("area_ids", [area_id]),
                "weekly_profile": {str(k): v for k, v in weekly_profile.items()},
            },
            "stage2_features": {
                "feature_names": feature_names,
                "total_samples": len(y_vector),
                "prophet_points": len(prophet_rows),
                "sample_rows": sample_rows[:4],
            },
            "stage3_inference": {
                "area_id": area_id,
                "day_of_week": day_of_week,
                # Chưa nạp model LightGBM/Prophet nào: ghi đúng phương pháp đang chạy (A-11/12).
                "model_version": "heuristic-baseline" if is_fallback else "profile-7x24",
                "is_fallback": is_fallback,
                "peak_hour": peak_hour,
                "peak_occupancy_pct": peak_occ,
                "recommended_surge_multiplier": rec_mult,
                "hourly_predictions": hourly_predictions,
                "surge_quote": {
                    "area_id": area_id,
                    "occupancy_pct": peak_occ,
                    "current_occupancy_pct": peak_occ,
                    "base_hourly_rate": base_hourly_rate,
                    "surge_multiplier": rec_mult,
                    "effective_hourly_rate": effective_rate,
                    "tier_label": "CRITICAL_SURGE" if peak_occ >= 85.0 else ("MODERATE_SURGE" if peak_occ >= 75.0 else "STANDARD"),
                    "reason": rec_reason,
                    "reason_code": rec_reason,
                },
            },
        }


    async def get_runtime_settings(self, actor: ConsoleActor) -> dict[str, Any]:
        if not any(access_policy.can(actor, p) for p in ("ai:metrics:read", "ai:member:manage", "ai:audit:read")):
            access_policy.require(actor, "ai:metrics:read")
        cfg = get_config()
        hardware = await asyncio.to_thread(_hardware_telemetry)
        return {
            "hardware": hardware,
            "compute": {
                "profile": _detect_compute_profile(cfg),
                "vision_device": cfg.vision.device,
                "vision_resolved_device": cfg.vision.resolved_device,
                "onnx_enabled": bool(cfg.vision.onnx_enabled),
                "vision_warmup_on_start": bool(cfg.vision.vision_warmup_on_start),
                "local_llm_gpu_layers": int(cfg.llm.local_llm_gpu_layers),
                "local_llm_ctx_size": int(cfg.llm.local_llm_ctx_size),
                "local_llm_threads": int(cfg.llm.local_llm_threads),
                "local_llm_parallel_slots": int(cfg.llm.local_llm_parallel_slots),
            },
            "models": await _effective_models(),
            "policy": {
                "rag_min_similarity": float(cfg.llm.rag_min_similarity),
                "rag_top_k": int(cfg.llm.rag_top_k),
                "llm_timeout_seconds": float(cfg.llm.llm_timeout_seconds),
                "llm_max_output_tokens": int(cfg.llm.llm_max_output_tokens),
                "vehicle_min_confidence": float(cfg.vision.vehicle_min_confidence),
                "default_lane_id": str(cfg.vision.lane_id),
                "telemetry_enabled": bool(cfg.telemetry.enabled),
                "telemetry_retention_days": int(cfg.telemetry.retention_days),
                "vision_retention_days": int(cfg.console.vision_retention_days),
            },
            "engines": await asyncio.to_thread(_engine_status, cfg.vision),
        }

    async def update_compute_settings(self, actor: ConsoleActor, payload: dict[str, Any]) -> dict[str, Any]:
        if not (access_policy.can(actor, "ai:prompt:edit") or access_policy.can(actor, "ai:model:evaluate")):
            access_policy.require(actor, "ai:prompt:edit")
        cfg = get_config()
        snapshot = snapshot_runtime_fields(cfg)
        try:
            self._apply_compute(cfg, payload)
        except Exception:
            # Ghi file lỗi thì hoàn tác RAM, để API báo lỗi đúng với cấu hình đang chạy (A-53).
            restore_runtime_fields(cfg, snapshot)
            raise
        summary = (
            f"vision={cfg.vision.device}(onnx={cfg.vision.onnx_enabled}), "
            f"llm={cfg.llm.llm_provider}(gpu_layers={cfg.llm.local_llm_gpu_layers}, "
            f"ctx={cfg.llm.local_llm_ctx_size}, threads={cfg.llm.local_llm_threads})"
        )
        await self.store.add_audit(actor.member_id, "settings.compute", "runtime_config", "compute", summary)

        # Tự động Hot Reload mô hình LLM nếu có thay đổi thông số phần cứng LLM
        llm_changed = any(
            k in payload and payload[k] is not None
            for k in (
                "local_llm_gpu_layers", "local_llm_ctx_size",
                "local_llm_threads", "local_llm_parallel_slots", "preset",
            )
        )
        if llm_changed and cfg.llm.llm_provider in LOCAL_LLM_PROVIDERS:
            try:
                await asyncio.to_thread(_reload_llm, cfg)
            except Exception as exc:
                logger.warning("Không thể tự động nạp lại LLM sau khi lưu cấu hình: %s", exc)

        return await self.get_runtime_settings(actor)

    @staticmethod
    def _apply_compute(cfg, payload: dict[str, Any]) -> None:
        preset = payload.get("preset")
        if preset == "safe_4gb":
            cfg.vision.device = "cpu"
            cfg.vision.onnx_enabled = True
            cfg.llm.local_llm_gpu_layers = 33
            cfg.llm.local_llm_ctx_size = 4096
            cfg.llm.local_llm_parallel_slots = 1
        elif preset == "cpu_eco":
            cfg.vision.device = "cpu"
            cfg.vision.onnx_enabled = True
            cfg.llm.local_llm_gpu_layers = 0
            cfg.llm.local_llm_ctx_size = 2048
            cfg.llm.local_llm_parallel_slots = 1
        elif preset == "gpu_full":
            cfg.vision.device = "cuda"
            cfg.vision.onnx_enabled = True
            cfg.llm.local_llm_gpu_layers = 33
            cfg.llm.local_llm_ctx_size = 4096
            cfg.llm.local_llm_parallel_slots = 2
        else:
            if "vision_device" in payload and payload["vision_device"] in ("auto", "cuda", "cpu"):
                cfg.vision.device = payload["vision_device"]
            if "onnx_enabled" in payload and payload["onnx_enabled"] is not None:
                cfg.vision.onnx_enabled = bool(payload["onnx_enabled"])
            if "vision_warmup_on_start" in payload and payload["vision_warmup_on_start"] is not None:
                cfg.vision.vision_warmup_on_start = bool(payload["vision_warmup_on_start"])
            if payload.get("llm_provider") or payload.get("llm_model"):
                # ADR-0061 §2: model theo tác vụ đổi bằng revision, không qua Settings.
                raise ValueError("Đổi provider/model ở trang Models & Connections, không ở Settings.")
            if "local_llm_gpu_layers" in payload and payload["local_llm_gpu_layers"] is not None:
                cfg.llm.local_llm_gpu_layers = max(0, min(64, int(payload["local_llm_gpu_layers"])))
            if "local_llm_ctx_size" in payload and payload["local_llm_ctx_size"] is not None:
                cfg.llm.local_llm_ctx_size = max(512, min(32768, int(payload["local_llm_ctx_size"])))
            if "local_llm_threads" in payload and payload["local_llm_threads"] is not None:
                cfg.llm.local_llm_threads = max(1, min(64, int(payload["local_llm_threads"])))
            if "local_llm_parallel_slots" in payload and payload["local_llm_parallel_slots"] is not None:
                cfg.llm.local_llm_parallel_slots = max(1, min(8, int(payload["local_llm_parallel_slots"])))

        overrides = {
            "vision_device": cfg.vision.device,
            "onnx_enabled": cfg.vision.onnx_enabled,
            "vision_warmup_on_start": cfg.vision.vision_warmup_on_start,
            "local_llm_gpu_layers": cfg.llm.local_llm_gpu_layers,
            "local_llm_ctx_size": cfg.llm.local_llm_ctx_size,
            "local_llm_threads": cfg.llm.local_llm_threads,
            "local_llm_parallel_slots": cfg.llm.local_llm_parallel_slots,
        }
        persist_runtime_overrides(overrides)

    async def update_policy_settings(self, actor: ConsoleActor, payload: dict[str, Any]) -> dict[str, Any]:
        access_policy.require(actor, "ai:policy:threshold")
        cfg = get_config()
        snapshot = snapshot_runtime_fields(cfg)
        try:
            if "rag_min_similarity" in payload and payload["rag_min_similarity"] is not None:
                cfg.llm.rag_min_similarity = round(max(0.05, min(0.95, float(payload["rag_min_similarity"]))), 2)
            if "rag_top_k" in payload and payload["rag_top_k"] is not None:
                cfg.llm.rag_top_k = max(1, min(20, int(payload["rag_top_k"])))
            if "llm_timeout_seconds" in payload and payload["llm_timeout_seconds"] is not None:
                cfg.llm.llm_timeout_seconds = max(5.0, min(300.0, float(payload["llm_timeout_seconds"])))
            if "llm_max_output_tokens" in payload and payload["llm_max_output_tokens"] is not None:
                cfg.llm.llm_max_output_tokens = max(128, min(8192, int(payload["llm_max_output_tokens"])))
            if "vehicle_min_confidence" in payload and payload["vehicle_min_confidence"] is not None:
                cfg.vision.vehicle_min_confidence = round(max(0.1, min(0.99, float(payload["vehicle_min_confidence"]))), 2)
            if "default_lane_id" in payload and payload["default_lane_id"]:
                cfg.vision.lane_id = str(payload["default_lane_id"]).strip()[:64]
            if "telemetry_enabled" in payload and payload["telemetry_enabled"] is not None:
                cfg.telemetry.enabled = bool(payload["telemetry_enabled"])
            if "telemetry_retention_days" in payload and payload["telemetry_retention_days"] is not None:
                cfg.telemetry.retention_days = max(1, min(365, int(payload["telemetry_retention_days"])))
            if "vision_retention_days" in payload and payload["vision_retention_days"] is not None:
                cfg.console.vision_retention_days = max(1, min(365, int(payload["vision_retention_days"])))

            persist_runtime_overrides({
                "rag_min_similarity": cfg.llm.rag_min_similarity,
                "rag_top_k": cfg.llm.rag_top_k,
                "llm_timeout_seconds": cfg.llm.llm_timeout_seconds,
                "llm_max_output_tokens": cfg.llm.llm_max_output_tokens,
                "vehicle_min_confidence": cfg.vision.vehicle_min_confidence,
                "default_lane_id": cfg.vision.lane_id,
                "telemetry_enabled": cfg.telemetry.enabled,
                "telemetry_retention_days": cfg.telemetry.retention_days,
                "vision_retention_days": cfg.console.vision_retention_days,
            })
        except Exception:
            restore_runtime_fields(cfg, snapshot)
            raise
        summary = (
            f"rag_min_sim={cfg.llm.rag_min_similarity}, top_k={cfg.llm.rag_top_k}, "
            f"vehicle_conf={cfg.vision.vehicle_min_confidence}, lane={cfg.vision.lane_id}; "
            f"lý do: {str(payload.get('reason') or '').strip()[:200]}"
        )
        await self.store.add_audit(actor.member_id, "settings.policy", "runtime_config", "policy", summary)
        return await self.get_runtime_settings(actor)

    async def engine_action(self, actor: ConsoleActor, action: str) -> dict[str, Any]:
        if not (access_policy.can(actor, "ai:model:evaluate") or access_policy.can(actor, "ai:prompt:edit")):
            access_policy.require(actor, "ai:model:evaluate")
        cfg = get_config()
        from app.core.vision.engines.anpr import model_loader as anpr_models

        if action == "unload":
            res = await asyncio.to_thread(anpr_models.unload_models)
            await self.store.add_audit(
                actor.member_id, "engine.unload", "vision_engine", "anpr",
                f"Giải phóng model Vision (yolo={res['unloaded_yolo']}, ocr={res['unloaded_ocr']})",
            )
        elif action == "warmup":
            ok = await asyncio.to_thread(anpr_models.warmup)
            await self.store.add_audit(
                actor.member_id, "engine.warmup", "vision_engine", "anpr",
                f"Nạp sẵn model Vision (ready={ok})",
            )
        elif action in ("reload_llm", "restart_llm"):
            res = await asyncio.to_thread(_reload_llm, cfg)
            await self.store.add_audit(
                actor.member_id, "engine.reload_llm", "llm_engine", getattr(cfg.llm, "llm_provider", "local"),
                f"Nạp lại mô hình LLM ({res.get('model', 'OK')})",
            )
        else:
            raise ValueError("Hành động engine chỉ nhận 'warmup', 'unload' hoặc 'reload_llm'.")
        return await self.get_runtime_settings(actor)

    async def list_sessions(self, actor: ConsoleActor) -> list[dict[str, Any]]:
        if not any(access_policy.can(actor, p) for p in ("ai:metrics:read", "ai:member:manage", "ai:audit:read")):
            access_policy.require(actor, "ai:metrics:read")
        include_all = access_policy.can(actor, "ai:member:manage")
        rows = await self.store.list_active_sessions(actor.member_id, include_all=include_all)
        return [
            {
                **r,
                "is_current": r["session_id"] == getattr(actor, "session_id", ""),
            }
            for r in rows
        ]

    async def revoke_session_by_id(self, actor: ConsoleActor, session_id: str, reason: str = "") -> dict[str, Any]:
        if not any(access_policy.can(actor, p) for p in ("ai:metrics:read", "ai:member:manage", "ai:audit:read")):
            access_policy.require(actor, "ai:metrics:read")
        if session_id and session_id == getattr(actor, "session_id", ""):
            raise ValueError("Không thể tự thu hồi phiên đang hoạt động hiện tại.")
        allow_any = access_policy.can(actor, "ai:member:manage")
        clean_reason = (reason or "").strip()[:200] or "Thu hồi phiên đăng nhập từ trang Cài đặt"
        revoked = await self.store.revoke_target_session(
            session_id, actor.member_id, allow_any_member=allow_any, reason=clean_reason
        )
        return {"session_id": session_id, "revoked": bool(revoked)}


tools_service = ToolsService()
