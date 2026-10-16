import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from '@/api/client';
import { consoleApi } from '@/api/console';
import { QUERY_KEYS } from '@/api/queryKeys';
import type { Permission, TurnFilter, Verdict } from '@/api/types';

export function useMe() {
  return useQuery({
    queryKey: QUERY_KEYS.ME,
    queryFn: consoleApi.me,
    // 401 = chưa đăng nhập, là trạng thái chứ không phải lỗi cần thử lại.
    retry: (count, error) => !(error instanceof ApiError && error.status === 401) && count < 2,
  });
}

export function useCan(permission: Permission): boolean {
  const { data } = useMe();
  return data?.permissions.includes(permission) ?? false;
}

export function usePasswordLogin() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) => consoleApi.passwordLogin(email, password),
    onSuccess: () => client.invalidateQueries({ queryKey: QUERY_KEYS.ME }),
  });
}

export function useEnrollTotp() {
  return useMutation({ mutationFn: consoleApi.enrollTotp });
}

export function useVerifyTotp() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: consoleApi.verifyTotp,
    onSuccess: () => client.invalidateQueries({ queryKey: QUERY_KEYS.ME }),
  });
}

export function useLogout() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: consoleApi.logout,
    onSettled: () => client.resetQueries(),
  });
}

export function useUsage(days: number) {
  return useQuery({ queryKey: QUERY_KEYS.USAGE(days), queryFn: () => consoleApi.usage(days) });
}

export function useReviewStats(days: number) {
  return useQuery({ queryKey: QUERY_KEYS.REVIEW_STATS(days), queryFn: () => consoleApi.reviewStats(days) });
}

export function useTurns(filter: TurnFilter) {
  return useInfiniteQuery({
    queryKey: QUERY_KEYS.TURNS(filter),
    queryFn: ({ pageParam }) => consoleApi.turns(filter, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => (last.length === 50 ? last[last.length - 1]?.at : undefined),
  });
}

export function useReviewTurn() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ turnId, verdict, note }: { turnId: string; verdict: Verdict; note: string }) =>
      consoleApi.reviewTurn(turnId, verdict, note),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: QUERY_KEYS.TURNS_ALL });
      void client.invalidateQueries({ queryKey: QUERY_KEYS.REVIEW_STATS_ALL });
    },
  });
}

export function useMembers() {
  return useQuery({ queryKey: QUERY_KEYS.MEMBERS, queryFn: consoleApi.members });
}

function useMemberMutation<A>(fn: (args: A) => Promise<unknown>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: QUERY_KEYS.MEMBERS });
      void client.invalidateQueries({ queryKey: QUERY_KEYS.AUDIT });
    },
  });
}

export function useInvite() {
  return useMemberMutation((a: { email: string; displayName: string; reason: string }) =>
    consoleApi.invite(a.email, a.displayName, a.reason),
  );
}

export function useRoleChange() {
  return useMemberMutation((a: { memberId: string; role: string; reason: string; grant: boolean }) =>
    a.grant ? consoleApi.grantRole(a.memberId, a.role, a.reason) : consoleApi.revokeRole(a.memberId, a.role, a.reason),
  );
}

export function useAudit() {
  return useQuery({ queryKey: QUERY_KEYS.AUDIT, queryFn: () => consoleApi.audit() });
}
