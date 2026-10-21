import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/constants/queryKeys';
import { grantRole, inviteMember, revokeRole } from '@/services/apiEndpoints/member.endpoint';
import type { InviteMemberRequest, RoleChangeRequest } from '@/types/member';

function useMemberMutation<A, R>(fn: (args: A) => Promise<R>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.members.list() });
      void client.invalidateQueries({ queryKey: queryKeys.audit.list() });
    },
  });
}

export function useInviteMutation() {
  return useMemberMutation((a: InviteMemberRequest) => inviteMember(a.email, a.displayName, a.reason));
}

export function useRoleChangeMutation() {
  return useMemberMutation((a: RoleChangeRequest) =>
    a.grant ? grantRole(a.memberId, a.role, a.reason) : revokeRole(a.memberId, a.role, a.reason),
  );
}

export const useInvite = useInviteMutation;
export const useRoleChange = useRoleChangeMutation;
