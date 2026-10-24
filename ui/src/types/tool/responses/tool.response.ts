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
