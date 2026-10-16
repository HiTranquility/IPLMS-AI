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
