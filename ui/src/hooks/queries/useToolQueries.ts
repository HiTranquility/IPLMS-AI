import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/constants/queryKeys';
import { getDocumentChunks, getKnowledgeDocuments, getSystemCheck } from '@/services/apiEndpoints/tool.endpoint';

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
