import type { ReactNode } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useMeQuery } from '@/hooks/queries/useAuthQueries';

export interface AnonymousGuardProps {
  children?: ReactNode;
  redirectTo?: string;
}

export function AnonymousGuard({ children, redirectTo = '/' }: AnonymousGuardProps) {
  const me = useMeQuery();

  if (me.data?.mfa_done) {
    return <Navigate to={redirectTo} replace />;
  }

  return children ? <>{children}</> : <Outlet />;
}

export default AnonymousGuard;
