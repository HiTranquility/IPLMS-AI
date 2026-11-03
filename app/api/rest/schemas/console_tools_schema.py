"""Pydantic schemas cho AI Console Tools & Settings REST routes."""
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Hợp đồng body của Chat Studio (ai bug-017). Giữ khớp với
# ui/src/pages/Copilot/components/ChatStudio/askContract.ts (ASK_BODY_FIELDS);
# test/test_console_tools.py và ChatStudio.test.tsx đối chiếu danh sách này.
ASK_BODY_FIELDS = ("query", "parking_lot_id", "min_similarity", "top_k", "temperature", "history")


class Check(BaseModel):
    key: str
    label: str
    ok: bool


class EngineStatus(BaseModel):
    # None = không biết chắc (UI hiện "—"), không có giá trị mặc định nào giả làm số đo.
    yolo_weights_path: str
    yolo_weights_bytes: Optional[int]
    yolo_version: str
    yolo_loaded: Optional[bool]
    ocr_languages: List[str]
    ocr_cache_dir: Optional[str]
    ocr_loaded: Optional[bool]
    onnx_enabled: bool
    torch_version: Optional[str]
    cuda_available: Optional[bool]


class SystemCheck(BaseModel):
    checks: List[Check]
    llm_model: str
    telemetry_enabled: bool
    vision_device: str
    telemetry_retention_days: int
    vision_retention_days: int
    engines: EngineStatus


class AnprTryOut(BaseModel):
    plate_number: str
    confidence: Optional[float]
    vehicle_type: Optional[str]
    plate_color: Optional[str]
    latency_ms: Optional[float]
    crop_image: Optional[str] = None
    crop_plate_image_url: Optional[str] = None


class ClipEventOut(BaseModel):
    plate_number: str
    confidence: float
    best_time_s: float
    start_time_s: float
    end_time_s: float
    frame_count: int
    crop_image: Optional[str] = None


class AnprClipOut(BaseModel):
    sampled_frames: int
    plate_reads: int
    latency_ms: float
    events: List[ClipEventOut]


class VerifyMatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_vehicle_type: str = Field(min_length=1, max_length=64)
    current_vehicle_type: str = Field(min_length=1, max_length=64)


class VerifyMatchOut(BaseModel):
    is_matched: bool
    similarity_score: Optional[float]
    mismatch_reason: str


class KnowledgeDocOut(BaseModel):
    id: str
    title: str
    category: str
    source: str
    chunk_count: int
    latest_version_no: int
    latest_status: str
    published_version_no: int
    updated_at: str


class DocumentChunkItem(BaseModel):
    ordinal: int
    section_title: str
    content: str


class DocumentVersionItem(BaseModel):
    version_no: int
    status: str
    chunk_count: int
    created_at: str
    published_at: str


class DocumentChunksOut(BaseModel):
    version_no: int
    status: str
    total: int
    chunks: List[DocumentChunkItem]
    versions: List[DocumentVersionItem]


class DeleteDocOut(BaseModel):
    deleted: int
    document_id: str


class ChatMessageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(pattern=r"^(user|assistant|system)$")
    content: str = Field(max_length=4000)


class AskIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    parking_lot_id: Optional[str] = Field(None, max_length=128)
    # Biên khớp thanh trượt Inspector. min_similarity chỉ làm truy xuất chặt hơn cấu hình
    # (rag_pipeline._limits), không nới được cổng NO_CONTEXT.
    min_similarity: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(None, ge=1, le=10)
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    history: Optional[List[ChatMessageIn]] = Field(None, max_length=10)

    def tuning(self) -> dict:
        return {
            "top_k": self.top_k,
            "min_similarity": self.min_similarity,
            "temperature": self.temperature,
            "history": [h.model_dump() for h in self.history] if self.history else None,
        }


class IngestOut(BaseModel):
    document_id: str
    status: str
    ok: bool
    chunk_count: int
    duration_ms: float
    message: str
    version_id: str
    version_no: int


class ForecastSimulateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    area_id: str = Field(default="AREA_CENTRAL_01", min_length=1, max_length=128)
    day_of_week: int = Field(default=4, ge=0, le=6)
    total_capacity: int = Field(default=350, ge=10, le=10000)
    base_hourly_rate: float = Field(default=25000.0, ge=0.0)


class ForecastLakeArea(BaseModel):
    area_id: str
    records: int


class ForecastAreasOut(BaseModel):
    source_path: str
    areas: List[ForecastLakeArea]


class ComputeSettingsIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    preset: Optional[str] = Field(None, max_length=32)
    vision_device: Optional[str] = Field(None, max_length=16)
    onnx_enabled: Optional[bool] = None
    vision_warmup_on_start: Optional[bool] = None
    local_llm_gpu_layers: Optional[int] = Field(None, ge=0, le=64)
    local_llm_ctx_size: Optional[int] = Field(None, ge=512, le=32768)
    local_llm_threads: Optional[int] = Field(None, ge=1, le=64)
    local_llm_parallel_slots: Optional[int] = Field(None, ge=1, le=8)

    @model_validator(mode="before")
    @classmethod
    def reject_model_fields(cls, data: Any) -> Any:
        # extra="ignore" sẽ nuốt im hai trường này và báo lưu thành công mà không có tác dụng
        # (REQ-020 X2); model theo tác vụ đổi bằng revision ở Models & Connections (ADR-0061 §2).
        if isinstance(data, dict) and ({"llm_provider", "llm_model"} & data.keys()):
            raise ValueError("Đổi provider/model ở trang Models & Connections, không ở Settings.")
        return data


class PolicySettingsIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rag_min_similarity: Optional[float] = Field(None, ge=0.05, le=0.95)
    rag_top_k: Optional[int] = Field(None, ge=1, le=20)
    llm_timeout_seconds: Optional[float] = Field(None, ge=5.0, le=300.0)
    llm_max_output_tokens: Optional[int] = Field(None, ge=128, le=8192)
    vehicle_min_confidence: Optional[float] = Field(None, ge=0.1, le=0.99)
    default_lane_id: Optional[str] = Field(None, max_length=64)
    telemetry_enabled: Optional[bool] = None
    telemetry_retention_days: Optional[int] = Field(None, ge=1, le=365)
    vision_retention_days: Optional[int] = Field(None, ge=1, le=365)
    reason: str = Field(..., min_length=3, max_length=500)


class EngineActionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(..., pattern="^(warmup|unload|reload_llm|restart_llm)$")


class RevokeSessionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: Optional[str] = Field("", max_length=200)


__all__ = [
    "ASK_BODY_FIELDS",
    "AnprClipOut",
    "AnprTryOut",
    "AskIn",
    "ChatMessageIn",
    "Check",
    "ClipEventOut",
    "ComputeSettingsIn",
    "DeleteDocOut",
    "DocumentChunkItem",
    "DocumentChunksOut",
    "DocumentVersionItem",
    "EngineActionIn",
    "EngineStatus",
    "ForecastAreasOut",
    "ForecastLakeArea",
    "ForecastSimulateIn",
    "IngestOut",
    "KnowledgeDocOut",
    "PolicySettingsIn",
    "RevokeSessionIn",
    "SystemCheck",
    "VerifyMatchIn",
    "VerifyMatchOut",
]
