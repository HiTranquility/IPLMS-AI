export interface UsageDay {
  date: string;
  requests: number;
  errors: number;
  refused: number;
  avg_latency_ms: number;
  speed_tok_s?: number;
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
  speed_tok_s?: number | null;
  context_tokens?: number | null;
  context_limit?: number | null;
}
