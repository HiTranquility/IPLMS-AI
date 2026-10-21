import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/constants/queryKeys';
import { getAudit } from '@/services/apiEndpoints/audit.endpoint';

export function useAuditQuery() {
  return useQuery({
    queryKey: queryKeys.audit.list(),
    queryFn: () => getAudit(),
  });
}

export const useAudit = useAuditQuery;
