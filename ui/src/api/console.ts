import { request, requestOne } from './client';
import type { AuditEntry, Me, Member, ReviewStats, Turn, TurnFilter, UsageSummary, Verdict } from './types';

export const consoleApi = {
  me: () => requestOne<Me>('/me'),
  passwordLogin: (email: string, password: string) =>
    requestOne<{ mfa_required: boolean }>('/auth/password', { method: 'POST', body: { email, password } }),
  enrollTotp: () => requestOne<{ otpauth_uri: string }>('/auth/totp/enroll', { method: 'POST' }),
  verifyTotp: (code: string) => requestOne<{ mfa_required: boolean }>('/auth/totp', { method: 'POST', body: { code } }),
  logout: () => request<never>('/auth/logout', { method: 'POST' }),

  usage: (days: number) => requestOne<UsageSummary>(`/copilot/usage?days=${days}`),
  reviewStats: (days: number) => requestOne<ReviewStats>(`/copilot/review-stats?days=${days}`),
  turns: (filter: TurnFilter, before?: string) => {
    const params = new URLSearchParams({ limit: '50' });
    if (filter.status) params.set('status', filter.status);
    if (filter.feedback !== undefined) params.set('feedback', String(filter.feedback));
    if (before) params.set('before', before);
    return request<Turn>(`/copilot/turns?${params}`);
  },
  reviewTurn: (turnId: string, verdict: Verdict, note: string) =>
    requestOne<{ turn_id: string; verdict: Verdict }>(`/copilot/turns/${turnId}/review`, {
      method: 'POST',
      body: { verdict, note },
    }),

  members: () => request<Member>('/members'),
  invite: (email: string, displayName: string, reason: string) =>
    requestOne<Member>('/members', { method: 'POST', body: { email, display_name: displayName, reason } }),
  grantRole: (memberId: string, role: string, reason: string) =>
    requestOne<{ changed: boolean }>(`/members/${memberId}/roles/${role}`, { method: 'POST', body: { reason } }),
  revokeRole: (memberId: string, role: string, reason: string) =>
    requestOne<{ changed: boolean }>(`/members/${memberId}/roles/${role}/revoke`, { method: 'POST', body: { reason } }),
  audit: (limit = 200) => request<AuditEntry>(`/audit?limit=${limit}`),
};
