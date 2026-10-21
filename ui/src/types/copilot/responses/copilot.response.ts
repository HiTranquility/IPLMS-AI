import type { UsageDay, Verdict } from '../shares/copilot.item';

export interface UsageSummary {
  window_days: number;
  total_requests: number;
  success_requests: number;
  refused_requests: number;
  no_context_requests: number;
  error_requests: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  avg_speed_tok_s?: number;
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

export type ReviewTurnResponse = {
  turn_id: string;
  verdict: Verdict;
};
