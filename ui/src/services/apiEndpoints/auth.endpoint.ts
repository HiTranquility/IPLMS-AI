import { apiClient, API_BASE } from '../apiClient';
import type { AuthMfaResponse, EnrollTotpResponse, Me } from '@/types/auth';

export const AUTH_ENDPOINTS = {
  ME: '/me',
  GOOGLE_START: `${API_BASE}/auth/google/start`,
  PASSWORD_LOGIN: '/auth/password',
  TOTP_ENROLL: '/auth/totp/enroll',
  TOTP_VERIFY: '/auth/totp',
  STEP_UP: '/auth/step-up',
  LOGOUT: '/auth/logout',
} as const;

export const getMe = (): Promise<Me> => apiClient.getOne<Me>(AUTH_ENDPOINTS.ME);

export const passwordLogin = (email: string, password: string): Promise<AuthMfaResponse> =>
  apiClient.postOne<AuthMfaResponse>(AUTH_ENDPOINTS.PASSWORD_LOGIN, { email, password });

export const enrollTotp = (): Promise<EnrollTotpResponse> =>
  apiClient.postOne<EnrollTotpResponse>(AUTH_ENDPOINTS.TOTP_ENROLL);

export const verifyTotp = (code: string): Promise<AuthMfaResponse> =>
  apiClient.postOne<AuthMfaResponse>(AUTH_ENDPOINTS.TOTP_VERIFY, { code });

export const stepUp = (code: string, reason: string): Promise<AuthMfaResponse> =>
  apiClient.postOne<AuthMfaResponse>(AUTH_ENDPOINTS.STEP_UP, { code, reason });

export const logout = (): Promise<never[]> => apiClient.post<never>(AUTH_ENDPOINTS.LOGOUT);

export const authApi = {
  me: getMe,
  passwordLogin,
  enrollTotp,
  verifyTotp,
  stepUp,
  logout,
};
