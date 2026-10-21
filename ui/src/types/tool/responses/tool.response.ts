import type { SystemCheckItem } from '../shares/tool.item';

export interface SystemCheck {
  checks: SystemCheckItem[];
  llm_model: string;
  telemetry_enabled: boolean;
  vision_device: string;
  telemetry_retention_days: number;
  vision_retention_days: number;
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
