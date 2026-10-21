import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/constants/queryKeys';
import { enrollTotp, logout, passwordLogin, stepUp, verifyTotp } from '@/services/apiEndpoints/auth.endpoint';
import type { PasswordLoginRequest, StepUpRequest } from '@/types/auth';

export function usePasswordLoginMutation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password }: PasswordLoginRequest) => passwordLogin(email, password),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.auth.me() }),
  });
}

export function useEnrollTotpMutation() {
  return useMutation({ mutationFn: enrollTotp });
}

export function useVerifyTotpMutation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: verifyTotp,
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.auth.me() }),
  });
}

export function useLogoutMutation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: logout,
    onSettled: () => client.resetQueries(),
  });
}

export function useStepUpMutation() {
  return useMutation({
    mutationFn: (a: StepUpRequest) => stepUp(a.code, a.reason),
  });
}

export const usePasswordLogin = usePasswordLoginMutation;
export const useEnrollTotp = useEnrollTotpMutation;
export const useVerifyTotp = useVerifyTotpMutation;
export const useLogout = useLogoutMutation;
