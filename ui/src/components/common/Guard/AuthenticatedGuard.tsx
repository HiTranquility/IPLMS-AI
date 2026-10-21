import type { ReactNode } from 'react';
import { Outlet } from 'react-router-dom';
import { ErrorBlock, Loading } from '../Ui/feedback/LoadState';
import { useMeQuery } from '@/hooks/queries/useAuthQueries';
import { useI18n } from '@/i18n/I18nProvider';
import { LoginPage } from '@/pages/Auth/LoginPage';
import { MfaPage } from '@/pages/Auth/MfaPage';
import { ApiError } from '@/services/apiClient';
import type { Me } from '@/types/auth';

export interface AuthenticatedGuardProps {
  children?: ReactNode | ((me: Me) => ReactNode);
}

export function AuthenticatedGuard({ children }: AuthenticatedGuardProps) {
  const { t } = useI18n();
  const me = useMeQuery();

  if (me.isPending) return <Loading label={t.app.checkingSession} />;
  if (me.error) {
    if (me.error instanceof ApiError && me.error.status === 401) return <LoginPage />;
    return <ErrorBlock error={me.error} onRetry={() => void me.refetch()} />;
  }
  if (!me.data.mfa_done) return <MfaPage me={me.data} />;

  if (typeof children === 'function') {
    return <>{children(me.data)}</>;
  }

  return children ? <>{children}</> : <Outlet />;
}

export default AuthenticatedGuard;
