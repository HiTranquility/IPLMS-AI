import type { Role } from '../../auth/shares/auth.item';

export type MemberStatus = 'INVITED' | 'ACTIVE' | 'DISABLED';

export interface Member {
  id: string;
  email: string;
  display_name: string;
  status: MemberStatus;
  created_at: string;
  roles: Role[];
}
