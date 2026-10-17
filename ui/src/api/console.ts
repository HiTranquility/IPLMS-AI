import { request, requestOne } from './client';
import type {
  AcceptPolicy, AccuracyReport, AuditEntry, CopilotAnswer, Decision, IngestResult, SystemCheck, EvalRun, LabelVerdict, Me, Member, ModelVersion,
  ReviewItem, ReviewStats, Turn, TurnFilter, UsageSummary, Verdict, VisionSample, VisionSnapshot, VisionStatus,
} from './types';

export interface ModelInput {
  name: string;
  version: string;
  artifact_key: string;
  sha256: string;
  note: string;
}

export const consoleApi = {
  me: () => requestOne<Me>('/me'),
  passwordLogin: (email: string, password: string) =>
    requestOne<{ mfa_required: boolean }>('/auth/password', { method: 'POST', body: { email, password } }),
  enrollTotp: () => requestOne<{ otpauth_uri: string }>('/auth/totp/enroll', { method: 'POST' }),
  verifyTotp: (code: string) => requestOne<{ mfa_required: boolean }>('/auth/totp', { method: 'POST', body: { code } }),
  logout: () => request<never>('/auth/logout', { method: 'POST' }),

  usage: (days: number) => requestOne<UsageSummary>(`/copilot/usage?days=${days}`),
  reviewStats: (days: number) => requestOne<ReviewStats>(`/copilot/review-stats?days=${days}`),
  turns: (filter: TurnFilter, before?: string) => {
    const params = new URLSearchParams({ limit: '50' });
    if (filter.status) params.set('status', filter.status);
    if (filter.feedback !== undefined) params.set('feedback', String(filter.feedback));
    if (before) params.set('before', before);
    return request<Turn>(`/copilot/turns?${params}`);
  },
  reviewTurn: (turnId: string, verdict: Verdict, note: string) =>
    requestOne<{ turn_id: string; verdict: Verdict }>(`/copilot/turns/${turnId}/review`, {
      method: 'POST',
      body: { verdict, note },
    }),

  members: () => request<Member>('/members'),
  invite: (email: string, displayName: string, reason: string) =>
    requestOne<Member>('/members', { method: 'POST', body: { email, display_name: displayName, reason } }),
  grantRole: (memberId: string, role: string, reason: string) =>
    requestOne<{ changed: boolean }>(`/members/${memberId}/roles/${role}`, { method: 'POST', body: { reason } }),
  revokeRole: (memberId: string, role: string, reason: string) =>
    requestOne<{ changed: boolean }>(`/members/${memberId}/roles/${role}/revoke`, { method: 'POST', body: { reason } }),
  audit: (limit = 200) => request<AuditEntry>(`/audit?limit=${limit}`),
  systemCheck: () => requestOne<SystemCheck>('/tools/system'),
  tryCopilot: (query: string, parkingLotId: string) =>
    requestOne<CopilotAnswer>('/tools/copilot', {
      method: 'POST',
      body: { query, parking_lot_id: parkingLotId || null },
    }),
  ingestDraft: (form: FormData) => requestOne<IngestResult>('/tools/knowledge', { method: 'POST', body: form }),
  stepUp: (code: string, reason: string) =>
    requestOne<{ mfa_required: boolean }>('/auth/step-up', { method: 'POST', body: { code, reason } }),

  visionStatus: () => requestOne<VisionStatus>('/vision/status'),
  labelQueue: () => request<VisionSample>('/vision/queue?limit=20'),
  addLabel: (captureId: string, verdict: LabelVerdict, plateText: string) =>
    requestOne<{ id: string }>(`/vision/samples/${captureId}/labels`, {
      method: 'POST',
      body: { verdict, plate_text: plateText },
    }),
  reviewQueue: () => request<ReviewItem>('/vision/reviews?limit=20'),
  decideLabel: (labelId: string, decision: Decision, note: string) =>
    requestOne<{ ok: boolean }>(`/vision/labels/${labelId}/decision`, { method: 'POST', body: { decision, note } }),
  snapshots: () => request<VisionSnapshot>('/vision/snapshots'),
  createSnapshot: (kind: 'train' | 'golden', name: string) =>
    requestOne<{ id: string; sample_count: number }>('/vision/snapshots', { method: 'POST', body: { kind, name } }),
  freezeSnapshot: (id: string, reason: string) =>
    requestOne<{ ok: boolean }>(`/vision/snapshots/${id}/freeze`, { method: 'POST', body: { reason } }),
  models: () => request<ModelVersion>('/vision/models'),
  registerModel: (input: ModelInput) => requestOne<{ id: string }>('/vision/models', { method: 'POST', body: input }),
  proposeModel: (id: string, reason: string) =>
    requestOne<{ ok: boolean }>(`/vision/models/${id}/propose`, { method: 'POST', body: { reason } }),
  promoteModel: (id: string, reason: string) =>
    requestOne<{ ok: boolean }>(`/vision/models/${id}/promote`, { method: 'POST', body: { reason } }),
  evals: () => request<EvalRun>('/vision/evals'),
  startEval: (snapshotId: string) =>
    requestOne<{ id: string }>('/vision/evals', { method: 'POST', body: { snapshot_id: snapshotId } }),
  accuracy: () => requestOne<AccuracyReport>('/vision/accuracy'),
  policies: () => request<AcceptPolicy>('/vision/policies'),
  proposePolicy: (threshold: number, auditRate: number, reason: string) =>
    requestOne<{ id: string; version: number }>('/vision/policies', {
      method: 'POST',
      body: { auto_accept_threshold: threshold, audit_rate: auditRate, reason },
    }),
  decidePolicy: (id: string, decision: Decision, note: string) =>
    requestOne<{ ok: boolean }>(`/vision/policies/${id}/decision`, { method: 'POST', body: { decision, note } }),
};
