import { apiClient } from '../apiClient';
import type { AuditEntry } from '@/types/audit';

export const AUDIT_ENDPOINTS = {
  LIST: (limit = 200) => `/audit?limit=${limit}`,
} as const;

export const getAudit = (limit = 200): Promise<AuditEntry[]> =>
  apiClient.get<AuditEntry>(AUDIT_ENDPOINTS.LIST(limit));

export const auditApi = {
  audit: getAudit,
};
