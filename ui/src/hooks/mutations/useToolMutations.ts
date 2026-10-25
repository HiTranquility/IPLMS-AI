import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/constants/queryKeys';
import { deleteKnowledgeDocument, ingestDraft, tryCopilot } from '@/services/apiEndpoints/tool.endpoint';
import type { TryCopilotRequest } from '@/types/tool';

export function useTryCopilotMutation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (a: TryCopilotRequest) => tryCopilot(a.query, a.parkingLotId),
    // Lượt thử hiện trong Copilot Lab để chấm.
    onSuccess: () => void client.invalidateQueries({ queryKey: queryKeys.copilot.turnsAll() }),
  });
}

export function useIngestDraftMutation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ingestDraft,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.audit.list() });
      void client.invalidateQueries({ queryKey: queryKeys.tools.all() });
    },
  });
}

export function useDeleteKnowledgeDocumentMutation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ documentId, parkingLotId }: { documentId: string; parkingLotId?: string }) =>
      deleteKnowledgeDocument(documentId, parkingLotId),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.tools.all() });
      void client.invalidateQueries({ queryKey: queryKeys.audit.list() });
    },
  });
}

export const useTryCopilot = useTryCopilotMutation;
export const useIngestDraft = useIngestDraftMutation;
export const useDeleteKnowledgeDocument = useDeleteKnowledgeDocumentMutation;
