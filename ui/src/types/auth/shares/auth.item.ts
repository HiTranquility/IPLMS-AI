export type Permission =
  | 'ai:metrics:read'
  | 'ai:task:label'
  | 'ai:label:approve'
  | 'ai:chatlog:read'
  | 'ai:pii:reveal'
  | 'ai:pipeline:manage'
  | 'ai:dataset:snapshot'
  | 'ai:golden:freeze'
  | 'ai:model:evaluate'
  | 'ai:model:propose'
  | 'ai:model:promote'
  | 'ai:prompt:edit'
  | 'ai:policy:threshold'
  | 'ai:member:manage'
  | 'ai:audit:read';

export const ROLES = [
  'ai_analyst',
  'ai_annotator',
  'ai_reviewer',
  'ai_data_engineer',
  'ai_ml_engineer',
  'ai_lead',
  'ai_console_admin',
] as const;

export type Role = (typeof ROLES)[number];

export interface Me {
  member_id: string;
  email: string;
  display_name: string;
  roles: Role[];
  permissions: Permission[];
  mfa_done: boolean;
  totp_enabled: boolean;
  totp_pending: boolean;
}
