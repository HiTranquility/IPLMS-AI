import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/constants/queryKeys';
import {
  getActiveSessions,
  getDocumentChunks,
  getKnowledgeDocuments,
  getRuntimeSettings,
  getSystemCheck,
} from '@/services/apiEndpoints/tool.endpoint';
import { getEvalCandidates } from '@/services/apiEndpoints/copilot.endpoint';

export function useSystemCheckQuery() {
  return useQuery({
    queryKey: queryKeys.tools.systemCheck(),
    queryFn: getSystemCheck,
  });
}

export const useSystemCheck = useSystemCheckQuery;

export function useKnowledgeDocumentsQuery(parkingLotId?: string) {
  return useQuery({
    queryKey: queryKeys.tools.knowledgeDocuments(parkingLotId),
    queryFn: () => getKnowledgeDocuments(parkingLotId),
  });
}

export const useKnowledgeDocuments = useKnowledgeDocumentsQuery;

export function useDocumentChunksQuery(documentId?: string, parkingLotId?: string, versionNo?: number) {
  return useQuery({
    queryKey: queryKeys.tools.documentChunks(documentId ?? '', parkingLotId, versionNo),
    queryFn: () => (documentId ? getDocumentChunks(documentId, parkingLotId, versionNo) : null),
    enabled: Boolean(documentId),
  });
}

export const useDocumentChunks = useDocumentChunksQuery;

export function useRuntimeSettingsQuery() {
  return useQuery({
    queryKey: queryKeys.tools.runtimeSettings(),
    queryFn: getRuntimeSettings,
  });
}

export const useRuntimeSettings = useRuntimeSettingsQuery;

export function useActiveSessionsQuery() {
  return useQuery({
    queryKey: queryKeys.tools.sessions(),
    queryFn: getActiveSessions,
  });
}

export const useActiveSessions = useActiveSessionsQuery;

export function useEvalCandidatesQuery() {
  return useQuery({
    queryKey: queryKeys.tools.evalCandidates(),
    queryFn: getEvalCandidates,
  });
}

export const useEvalCandidates = useEvalCandidatesQuery;
