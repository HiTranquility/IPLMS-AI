import type { AccuracyPoint } from '../shares/vision.item';

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
