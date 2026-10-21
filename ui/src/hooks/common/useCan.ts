import type { Permission } from '@/types/auth';
import { useMeQuery } from '../queries/useAuthQueries';

export function useCan(permission: Permission): boolean {
  const { data } = useMeQuery();
  return data?.permissions.includes(permission) ?? false;
}
