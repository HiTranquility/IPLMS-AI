import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/constants/queryKeys';
import { getKnowledgeDocuments, getSystemCheck } from '@/services/apiEndpoints/tool.endpoint';

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
