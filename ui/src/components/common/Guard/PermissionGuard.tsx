import type { ReactNode } from 'react';
import { allowed } from '@/components/layout/navigation';
import { Forbidden } from '../Shared/Forbidden';
import type { Me, Permission } from '@/types/auth';

export interface PermissionGuardProps {
  me: Me;
  permission: Permission | Permission[];
  children: ReactNode;
  fallback?: ReactNode;
}

export function PermissionGuard({ me, permission, children, fallback }: PermissionGuardProps) {
  const permissions = Array.isArray(permission) ? permission : [permission];
  return allowed({ permissions }, me.permissions) ? <>{children}</> : <>{fallback ?? <Forbidden />}</>;
}

export default PermissionGuard;
