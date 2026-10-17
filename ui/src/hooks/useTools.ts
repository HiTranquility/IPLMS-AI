import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { consoleApi } from '@/api/console';
import { QUERY_KEYS } from '@/api/queryKeys';

export const useSystemCheck = () => useQuery({ queryKey: QUERY_KEYS.SYSTEM_CHECK, queryFn: consoleApi.systemCheck });

export function useTryCopilot() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (a: { query: string; parkingLotId: string }) => consoleApi.tryCopilot(a.query, a.parkingLotId),
    // Lượt thử hiện trong Copilot Lab để chấm.
    onSuccess: () => void client.invalidateQueries({ queryKey: QUERY_KEYS.TURNS_ALL }),
  });
}

export function useIngestDraft() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: consoleApi.ingestDraft,
    onSuccess: () => void client.invalidateQueries({ queryKey: QUERY_KEYS.AUDIT }),
  });
}
