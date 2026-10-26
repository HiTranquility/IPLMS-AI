import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/constants/queryKeys';
import {
  deleteKnowledgeDocument,
  ingestDraft,
  revokeActiveSession,
  triggerEngineAction,
  tryCopilot,
  updateComputeSettings,
  updatePolicySettings,
} from '@/services/apiEndpoints/tool.endpoint';
import { promoteTurnToEval } from '@/services/apiEndpoints/copilot.endpoint';
import type { ComputeSettings, PolicySettings, TryCopilotRequest } from '@/types/tool';

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

export function useUpdateComputeSettingsMutation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<ComputeSettings> & { preset?: 'safe_4gb' | 'cpu_eco' | 'gpu_full' }) =>
      updateComputeSettings(payload),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.tools.all() });
      void client.invalidateQueries({ queryKey: queryKeys.audit.list() });
    },
  });
}

export function useUpdatePolicySettingsMutation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<PolicySettings> & { reason: string }) => updatePolicySettings(payload),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.tools.all() });
      void client.invalidateQueries({ queryKey: queryKeys.audit.list() });
    },
  });
}

export function useEngineActionMutation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (action: 'warmup' | 'unload') => triggerEngineAction(action),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.tools.all() });
      void client.invalidateQueries({ queryKey: queryKeys.audit.list() });
    },
  });
}

export function useRevokeSessionMutation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, reason }: { sessionId: string; reason?: string }) =>
      revokeActiveSession(sessionId, reason),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.tools.sessions() });
      void client.invalidateQueries({ queryKey: queryKeys.audit.list() });
    },
  });
}

export function usePromoteTurnToEvalMutation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: promoteTurnToEval,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.tools.evalCandidates() });
      void client.invalidateQueries({ queryKey: queryKeys.audit.list() });
    },
  });
}

export const useUpdateComputeSettings = useUpdateComputeSettingsMutation;
export const useUpdatePolicySettings = useUpdatePolicySettingsMutation;
export const useEngineAction = useEngineActionMutation;
export const useRevokeSession = useRevokeSessionMutation;
export const usePromoteTurnToEval = usePromoteTurnToEvalMutation;
