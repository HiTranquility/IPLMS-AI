import { apiClient } from '../apiClient';
import type { ReviewStats, ReviewTurnResponse, Turn, TurnFilter, UsageSummary, Verdict } from '@/types/copilot';

export const COPILOT_ENDPOINTS = {
  USAGE: (days: number) => `/copilot/usage?days=${days}`,
  REVIEW_STATS: (days: number) => `/copilot/review-stats?days=${days}`,
  TURNS: (params: URLSearchParams) => `/copilot/turns?${params}`,
  REVIEW_TURN: (turnId: string) => `/copilot/turns/${turnId}/review`,
  PROMOTE_EVAL: (turnId: string) => `/copilot/turns/${turnId}/promote-eval`,
  EVAL_CANDIDATES: '/copilot/eval-candidates',
} as const;

export const getUsage = (days: number): Promise<UsageSummary> =>
  apiClient.getOne<UsageSummary>(COPILOT_ENDPOINTS.USAGE(days));

export const getReviewStats = (days: number): Promise<ReviewStats> =>
  apiClient.getOne<ReviewStats>(COPILOT_ENDPOINTS.REVIEW_STATS(days));

export const getTurns = (filter: TurnFilter, before?: string): Promise<Turn[]> => {
  const params = new URLSearchParams({ limit: '50' });
  if (filter.status) params.set('status', filter.status);
  if (filter.feedback !== undefined) params.set('feedback', String(filter.feedback));
  if (before) params.set('before', before);
  return apiClient.get<Turn>(COPILOT_ENDPOINTS.TURNS(params));
};

export const reviewTurn = (turnId: string, verdict: Verdict, note: string): Promise<ReviewTurnResponse> =>
  apiClient.postOne<ReviewTurnResponse>(COPILOT_ENDPOINTS.REVIEW_TURN(turnId), { verdict, note });

export function promoteTurnToEval(payload: {
  turnId: string;
  query: string;
  expected_behavior: 'ANSWER' | 'REFUSE';
  category: string;
  note?: string;
}): Promise<Record<string, unknown>> {
  return apiClient.postOne<Record<string, unknown>>(COPILOT_ENDPOINTS.PROMOTE_EVAL(payload.turnId), {
    query: payload.query,
    expected_behavior: payload.expected_behavior,
    category: payload.category,
    note: payload.note ?? '',
  });
}

export function getEvalCandidates(): Promise<Array<Record<string, unknown>>> {
  return apiClient.get<Record<string, unknown>>(COPILOT_ENDPOINTS.EVAL_CANDIDATES);
}

export const copilotApi = {
  usage: getUsage,
  reviewStats: getReviewStats,
  turns: getTurns,
  reviewTurn,
  promoteTurnToEval,
  getEvalCandidates,
};
