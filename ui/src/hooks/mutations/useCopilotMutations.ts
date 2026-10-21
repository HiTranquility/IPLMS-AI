import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/constants/queryKeys';
import { reviewTurn } from '@/services/apiEndpoints/copilot.endpoint';
import type { ReviewTurnRequest } from '@/types/copilot';

export function useReviewTurnMutation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ turnId, verdict, note }: ReviewTurnRequest) => reviewTurn(turnId, verdict, note),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.copilot.turnsAll() });
      void client.invalidateQueries({ queryKey: queryKeys.copilot.reviewStatsAll() });
    },
  });
}

export const useReviewTurn = useReviewTurnMutation;
