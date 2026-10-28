import type { SystemCheckItem } from '../shares/tool.item';

export interface SystemCheck {
  checks: SystemCheckItem[];
  llm_model: string;
  telemetry_enabled: boolean;
  vision_device: string;
  telemetry_retention_days: number;
  vision_retention_days: number;
  /** Trạng thái engine Vision thật; null = server không biết chắc (UI hiện "—"). */
  engines?: EngineStatus;
}

export interface EngineStatus {
  yolo_weights_path: string;
  yolo_weights_bytes: number | null;
  yolo_version: string;
  yolo_loaded: boolean | null;
  ocr_languages: string[];
  ocr_cache_dir: string | null;
  ocr_loaded: boolean | null;
  onnx_enabled: boolean;
  torch_version: string | null;
  cuda_available: boolean | null;
}

export interface CopilotAnswer {
  answer: string;
  sources: string[];
  confidence: number;
  model_revision: string;
  turn_id: string;
  prompt_version: string;
}

export interface IngestResult {
  document_id: string;
  status: string;
  ok: boolean;
  chunk_count: number;
  duration_ms: number;
  message: string;
  version_id: string;
  version_no: number;
}

export interface HardwareTelemetry {
  cpu_logical_cores: number | null;
  ram_total_mb: number | null;
  ram_available_mb: number | null;
  ram_used_percent: number | null;
  cuda_available: boolean;
  gpu_name: string | null;
  vram_total_mb: number | null;
  vram_used_mb: number | null;
  vram_free_mb: number | null;
}

export interface ComputeSettings {
  profile: 'safe_4gb' | 'cpu_eco' | 'gpu_full' | 'custom';
  vision_device: string;
  vision_resolved_device: string;
  onnx_enabled: boolean;
  vision_warmup_on_start: boolean;
  local_llm_gpu_layers: number;
  local_llm_ctx_size: number;
  local_llm_threads: number;
  local_llm_parallel_slots: number;
}

/** Model inference dùng thật cho một tác vụ (ADR-0061 §2): revision ACTIVE, không có thì env. */
export interface EffectiveModel {
  task: 'copilot_answer' | 'test_generation' | 'test_judge';
  provider: string | null;
  model: string | null;
  source: 'profile' | 'env' | 'unknown';
  revision: number | null;
}

export interface PolicySettings {
  rag_min_similarity: number;
  rag_top_k: number;
  llm_timeout_seconds: number;
  llm_max_output_tokens: number;
  vehicle_min_confidence: number;
  default_lane_id: string;
  telemetry_enabled: boolean;
  telemetry_retention_days: number;
  vision_retention_days: number;
}

export interface RuntimeSettings {
  hardware: HardwareTelemetry;
  compute: ComputeSettings;
  policy: PolicySettings;
  engines: EngineStatus;
  models: EffectiveModel[];
}

export interface ActiveSession {
  session_id: string;
  member_id: string;
  email: string;
  display_name: string;
  created_at: string | null;
  last_seen_at: string | null;
  mfa_verified: boolean;
  step_up_at: string | null;
  is_current: boolean;
}

export interface EvalCandidate {
  turn_id: string;
  query: string;
  expected_behavior: 'ANSWER' | 'REFUSE';
  category: string;
  note: string;
  promoted_by: string;
  promoted_at: string;
}

/** Bãi có dữ liệu trong Gold lake: `area_id` chính là `area_key` mà Forecast tra (ai bug-028). */
export interface ForecastLakeArea {
  area_id: string;
  records: number;
}

export interface ForecastAreas {
  source_path: string;
  areas: ForecastLakeArea[];
}
