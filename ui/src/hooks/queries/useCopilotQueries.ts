import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/constants/queryKeys';
import { getEvalCandidates, getReviewStats, getTurns, getUsage } from '@/services/apiEndpoints/copilot.endpoint';
import type { TurnFilter } from '@/types/copilot';

export function useUsageQuery(days: number) {
  return useQuery({
    queryKey: queryKeys.copilot.usage(days),
    queryFn: () => getUsage(days),
  });
}

export function useReviewStatsQuery(days: number) {
  return useQuery({
    queryKey: queryKeys.copilot.reviewStats(days),
    queryFn: () => getReviewStats(days),
  });
}

export function useTurnsInfiniteQuery(filter: TurnFilter) {
  return useInfiniteQuery({
    queryKey: queryKeys.copilot.turns(filter),
    queryFn: ({ pageParam }) => getTurns(filter, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => (last.length === 50 ? last[last.length - 1]?.at : undefined),
  });
}

export function useCopilotEvalCandidatesQuery(enabled = true) {
  return useQuery({
    queryKey: queryKeys.tools.evalCandidates(),
    queryFn: getEvalCandidates,
    enabled,
  });
}

export const useUsage = useUsageQuery;
export const useReviewStats = useReviewStatsQuery;
export const useTurns = useTurnsInfiniteQuery;
export const useCopilotEvalCandidates = useCopilotEvalCandidatesQuery;
