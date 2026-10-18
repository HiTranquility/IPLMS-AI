/** Hợp đồng REST của AI Console — khớp model Pydantic ở `app/api/rest/routes/console_*`. */

export type Permission =
  | 'ai:metrics:read' | 'ai:task:label' | 'ai:label:approve' | 'ai:chatlog:read'
  | 'ai:pii:reveal' | 'ai:pipeline:manage' | 'ai:dataset:snapshot' | 'ai:golden:freeze'
  | 'ai:model:evaluate' | 'ai:model:propose' | 'ai:model:promote' | 'ai:prompt:edit'
  | 'ai:policy:threshold' | 'ai:member:manage' | 'ai:audit:read';

export const ROLES = [
  'ai_analyst', 'ai_annotator', 'ai_reviewer', 'ai_data_engineer',
  'ai_ml_engineer', 'ai_lead', 'ai_console_admin',
] as const;
export type Role = (typeof ROLES)[number];

export interface Me {
  member_id: string;
  email: string;
  display_name: string;
  roles: Role[];
  permissions: Permission[];
  mfa_done: boolean;
  totp_enabled: boolean;
  totp_pending: boolean;
}

export interface UsageDay {
  date: string;
  requests: number;
  errors: number;
  refused: number;
  avg_latency_ms: number;
}

export interface UsageSummary {
  window_days: number;
  total_requests: number;
  success_requests: number;
  refused_requests: number;
  no_context_requests: number;
  error_requests: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  cost_known: boolean;
  total_cost_usd: number;
  avg_cost_usd: number;
  thumbs_up: number;
  thumbs_down: number;
  days: UsageDay[];
}

export interface ReviewStats {
  window_days: number;
  reviewed: number;
  correct: number;
  incorrect: number;
  unsafe: number;
  accuracy: number | null;
}

export type TurnStatus = 'SUCCESS' | 'REFUSED' | 'NO_CONTEXT' | 'ERROR';
export type Verdict = 'CORRECT' | 'INCORRECT' | 'UNSAFE';

export interface TurnReview {
  verdict: Verdict;
  note: string;
  reviewer: string;
  reviewed_at: string;
}

export interface Turn {
  turn_id: string;
  at: string;
  task: string;
  status: TurnStatus;
  model: string;
  prompt_version: string;
  input_tokens: number | null;
  output_tokens: number | null;
  latency_ms: number;
  cost_usd: number | null;
  user_role: string;
  parking_lot_id: string;
  query: string;
  answer: string;
  error_code: string;
  feedback: 1 | -1 | null;
  review: TurnReview | null;
}

export interface TurnFilter {
  status?: TurnStatus;
  feedback?: 1 | -1;
}

export interface Member {
  id: string;
  email: string;
  display_name: string;
  status: 'INVITED' | 'ACTIVE' | 'DISABLED';
  created_at: string;
  roles: Role[];
}

export interface AuditEntry {
  id: string;
  actor_id: string;
  action: string;
  target_type: string;
  target_id: string;
  reason: string;
  at: string;
}

// ── Vision (ISSUE-126 P3–P5) ────────────────────────────────────────────────

export interface VisionSample {
  capture_id: string;
  image_sha256: string;
  machine_plate: string;
  machine_confidence: number | null;
  confirmed_plate: string;
  human_corrected: boolean;
  selection_reasons: string[];
  source_status: string;
  purpose: string;
  source_final_plate: string;
  group_ref: string;
  area_ref: string;
  captured_at: string | null;
  source_updated_at: string | null;
  imported_at: string | null;
}

export type LabelVerdict = 'CORRECT' | 'CORRECTED' | 'UNUSABLE';
export type Decision = 'APPROVED' | 'REJECTED';

export interface ReviewItem extends VisionSample {
  label: { id: string; verdict: LabelVerdict; plate_text: string; labeler: string; created_at: string };
}

export interface VisionStatus {
  sample_count: number;
  last_imported_at: string | null;
  watermark_at: string | null;
  recent_errors: { capture_id: string; reason: string; at: string }[];
  samples: number;
  pending_review: number;
  approved: number;
  rejected: number;
}

export interface VisionSnapshot {
  id: string;
  kind: 'train' | 'golden';
  name: string;
  samples_sha256: string;
  sample_count: number;
  created_by: string;
  created_at: string;
  frozen_by: string;
  frozen_at: string | null;
}

export type ModelStage = 'candidate' | 'proposed' | 'production' | 'retired';

export interface ModelVersion {
  id: string;
  name: string;
  version: string;
  artifact_key: string;
  sha256: string;
  train_snapshot_id: string;
  stage: ModelStage;
  note: string;
  registered_by: string;
  registered_at: string;
  proposed_by_id: string;
  proposed_by: string;
  proposed_at: string | null;
  approved_by: string;
  approved_at: string | null;
}

export interface EvalMetrics {
  total?: number;
  exact_match_strict?: number;
  exact_match_relaxed?: number;
  mean_cer?: number;
  errors?: number;
  [key: string]: unknown;
}

export interface EvalRun {
  id: string;
  kind: string;
  snapshot_id: string;
  snapshot_name: string;
  engine_version: string;
  metrics: EvalMetrics | null;
  status: 'RUNNING' | 'DONE' | 'FAILED';
  error: string;
  started_by: string;
  started_at: string;
  finished_at: string | null;
}

export interface AccuracyPoint {
  threshold: number;
  total: number;
  accuracy: number | null;
  coverage: number | null;
}

export interface AccuracyReport {
  total: number;
  correct: number;
  accuracy: number | null;
  interval_95: [number, number] | null;
  target: number;
  min_samples: number;
  buckets: { from: number; to: number; total: number; correct: number; accuracy: number | null }[];
  curve: AccuracyPoint[];
  suggested_threshold: number | null;
  suggestion_reason: string;
  truth_sources: { console: number; moderator: number };
}

export interface AcceptPolicy {
  id: string;
  model_name: string;
  version: number;
  auto_accept_threshold: number;
  audit_rate: number;
  status: 'PROPOSED' | 'APPROVED' | 'REJECTED';
  evidence: { audit_total?: number; audit_accuracy?: number | null; at_threshold?: AccuracyPoint | null };
  reason: string;
  proposed_by: string;
  proposed_by_id: string;
  proposed_at: string;
  decided_by: string;
  decided_at: string | null;
}

// ── Công cụ thử (IPLMS ADR-0050) ─────────────────────────────────────────────

export interface SystemCheck {
  checks: { key: string; label: string; ok: boolean }[];
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
