import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/constants/queryKeys';
import { getSystemCheck } from '@/services/apiEndpoints/tool.endpoint';

export function useSystemCheckQuery() {
  return useQuery({
    queryKey: queryKeys.tools.systemCheck(),
    queryFn: getSystemCheck,
  });
}

export const useSystemCheck = useSystemCheckQuery;
