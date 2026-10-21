import type { Me } from '../shares/auth.item';

export type MeResponse = Me;

export type AuthMfaResponse = {
  mfa_required: boolean;
};

export type EnrollTotpResponse = {
  otpauth_uri: string;
};
