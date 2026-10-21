import { apiClient } from '../apiClient';
import type { Member, RoleChangeResponse } from '@/types/member';

export const MEMBER_ENDPOINTS = {
  LIST: '/members',
  INVITE: '/members',
  GRANT_ROLE: (memberId: string, role: string) => `/members/${memberId}/roles/${role}`,
  REVOKE_ROLE: (memberId: string, role: string) => `/members/${memberId}/roles/${role}/revoke`,
} as const;

export const getMembers = (): Promise<Member[]> => apiClient.get<Member>(MEMBER_ENDPOINTS.LIST);

export const inviteMember = (email: string, displayName: string, reason: string): Promise<Member> =>
  apiClient.postOne<Member>(MEMBER_ENDPOINTS.INVITE, { email, display_name: displayName, reason });

export const grantRole = (memberId: string, role: string, reason: string): Promise<RoleChangeResponse> =>
  apiClient.postOne<RoleChangeResponse>(MEMBER_ENDPOINTS.GRANT_ROLE(memberId, role), { reason });

export const revokeRole = (memberId: string, role: string, reason: string): Promise<RoleChangeResponse> =>
  apiClient.postOne<RoleChangeResponse>(MEMBER_ENDPOINTS.REVOKE_ROLE(memberId, role), { reason });

export const memberApi = {
  members: getMembers,
  invite: inviteMember,
  grantRole,
  revokeRole,
};
