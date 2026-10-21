import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/constants/queryKeys';
import { getMembers } from '@/services/apiEndpoints/member.endpoint';

export function useMembersQuery() {
  return useQuery({
    queryKey: queryKeys.members.list(),
    queryFn: getMembers,
  });
}

export const useMembers = useMembersQuery;
