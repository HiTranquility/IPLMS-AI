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
