import { apiClient, API_BASE } from '../apiClient';
import type {
  AcceptPolicy,
  AccuracyReport,
  Decision,
  EvalRun,
  LabelVerdict,
  ModelInput,
  QualityFlag,
  ModelVersion,
  ReviewItem,
  VisionSample,
  VisionSnapshot,
  VisionStatus,
} from '@/types/vision';

export type { ModelInput };

export const VISION_ENDPOINTS = {
  STATUS: '/vision/status',
  QUEUE: (limit = 20) => `/vision/queue?limit=${limit}`,
  SAMPLE_CROP: (captureId: string) => `${API_BASE}/vision/samples/${captureId}/crop`,
  SAMPLE_LABELS: (captureId: string) => `/vision/samples/${captureId}/labels`,
  REVIEWS: (limit = 20) => `/vision/reviews?limit=${limit}`,
  LABEL_DECISION: (labelId: string) => `/vision/labels/${labelId}/decision`,
  SNAPSHOTS: '/vision/snapshots',
  SNAPSHOT_FREEZE: (id: string) => `/vision/snapshots/${id}/freeze`,
  MODELS: '/vision/models',
  MODEL_PROPOSE: (id: string) => `/vision/models/${id}/propose`,
  MODEL_PROMOTE: (id: string) => `/vision/models/${id}/promote`,
  EVALS: '/vision/evals',
  ACCURACY: '/vision/accuracy',
  POLICIES: '/vision/policies',
  POLICY_DECISION: (id: string) => `/vision/policies/${id}/decision`,
  SEED_DEMO: '/vision/seed-demo',
} as const;

export const seedDemoBatch = (): Promise<{ seeded_samples: number; seeded_reviews: number }> =>
  apiClient.postOne<{ seeded_samples: number; seeded_reviews: number }>(VISION_ENDPOINTS.SEED_DEMO, {});

export const getVisionStatus = (): Promise<VisionStatus> =>
  apiClient.getOne<VisionStatus>(VISION_ENDPOINTS.STATUS);

export const getLabelQueue = (): Promise<VisionSample[]> =>
  apiClient.get<VisionSample>(VISION_ENDPOINTS.QUEUE(20));

export const addLabel = (
  captureId: string,
  verdict: LabelVerdict,
  plateText: string,
  qualityFlags: QualityFlag[] = [],
): Promise<{ id: string }> =>
  apiClient.postOne<{ id: string }>(VISION_ENDPOINTS.SAMPLE_LABELS(captureId), {
    verdict,
    plate_text: plateText,
    quality_flags: qualityFlags,
  });

export const getReviewQueue = (): Promise<ReviewItem[]> =>
  apiClient.get<ReviewItem>(VISION_ENDPOINTS.REVIEWS(20));

export const decideLabel = (labelId: string, decision: Decision, note: string): Promise<{ ok: boolean }> =>
  apiClient.postOne<{ ok: boolean }>(VISION_ENDPOINTS.LABEL_DECISION(labelId), { decision, note });

export const getSnapshots = (): Promise<VisionSnapshot[]> =>
  apiClient.get<VisionSnapshot>(VISION_ENDPOINTS.SNAPSHOTS);

export const createSnapshot = (kind: 'train' | 'golden', name: string): Promise<{ id: string; sample_count: number }> =>
  apiClient.postOne<{ id: string; sample_count: number }>(VISION_ENDPOINTS.SNAPSHOTS, { kind, name });

export const freezeSnapshot = (id: string, reason: string): Promise<{ ok: boolean }> =>
  apiClient.postOne<{ ok: boolean }>(VISION_ENDPOINTS.SNAPSHOT_FREEZE(id), { reason });

export const getModels = (): Promise<ModelVersion[]> =>
  apiClient.get<ModelVersion>(VISION_ENDPOINTS.MODELS);

export const registerModel = (input: ModelInput): Promise<{ id: string }> =>
  apiClient.postOne<{ id: string }>(VISION_ENDPOINTS.MODELS, input);

export const proposeModel = (id: string, reason: string): Promise<{ ok: boolean }> =>
  apiClient.postOne<{ ok: boolean }>(VISION_ENDPOINTS.MODEL_PROPOSE(id), { reason });

export const promoteModel = (id: string, reason: string): Promise<{ ok: boolean }> =>
  apiClient.postOne<{ ok: boolean }>(VISION_ENDPOINTS.MODEL_PROMOTE(id), { reason });

export const getEvals = (): Promise<EvalRun[]> =>
  apiClient.get<EvalRun>(VISION_ENDPOINTS.EVALS);

export const startEval = (snapshotId: string): Promise<{ id: string }> =>
  apiClient.postOne<{ id: string }>(VISION_ENDPOINTS.EVALS, { snapshot_id: snapshotId });

export const getAccuracy = (): Promise<AccuracyReport> =>
  apiClient.getOne<AccuracyReport>(VISION_ENDPOINTS.ACCURACY);

export const getPolicies = (): Promise<AcceptPolicy[]> =>
  apiClient.get<AcceptPolicy>(VISION_ENDPOINTS.POLICIES);

export const proposePolicy = (threshold: number, auditRate: number, reason: string): Promise<{ id: string; version: number }> =>
  apiClient.postOne<{ id: string; version: number }>(VISION_ENDPOINTS.POLICIES, {
    auto_accept_threshold: threshold,
    audit_rate: auditRate,
    reason,
  });

export const decidePolicy = (id: string, decision: Decision, note: string): Promise<{ ok: boolean }> =>
  apiClient.postOne<{ ok: boolean }>(VISION_ENDPOINTS.POLICY_DECISION(id), { decision, note });

export const visionApi = {
  visionStatus: getVisionStatus,
  labelQueue: getLabelQueue,
  addLabel,
  reviewQueue: getReviewQueue,
  decideLabel,
  snapshots: getSnapshots,
  createSnapshot,
  freezeSnapshot,
  models: getModels,
  registerModel,
  proposeModel,
  promoteModel,
  evals: getEvals,
  startEval,
  accuracy: getAccuracy,
  policies: getPolicies,
  proposePolicy,
  decidePolicy,
};
