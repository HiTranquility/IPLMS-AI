import type { TurnFilter } from './types';

/** Một nguồn queryKey cho console (cùng luật QUERY_KEYS của frontend). */
export const QUERY_KEYS = {
  ME: ['me'] as const,
  USAGE: (days: number) => ['copilot', 'usage', days] as const,
  REVIEW_STATS: (days: number) => ['copilot', 'review-stats', days] as const,
  TURNS: (filter: TurnFilter) => ['copilot', 'turns', filter] as const,
  TURNS_ALL: ['copilot', 'turns'] as const,
  REVIEW_STATS_ALL: ['copilot', 'review-stats'] as const,
  MEMBERS: ['members'] as const,
  AUDIT: ['audit'] as const,
};
