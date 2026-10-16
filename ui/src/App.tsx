import type { ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { ApiError } from '@/api/client';
import type { Me, Permission } from '@/api/types';
import { Forbidden } from '@/components/common/Shared/Forbidden';
import { NotFound } from '@/components/common/Shared/NotFound';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { AppShell } from '@/components/layout/AppShell';
import { NAV_ITEMS } from '@/components/layout/navigation';
import { useMe } from '@/hooks/useConsole';
import { AuditPage } from '@/pages/audit/AuditPage';
import { LoginPage } from '@/pages/auth/LoginPage';
import { MfaPage } from '@/pages/auth/MfaPage';
import { CopilotLabPage } from '@/pages/copilot/CopilotLabPage';
import { MembersPage } from '@/pages/members/MembersPage';
import { OverviewPage } from '@/pages/overview/OverviewPage';

function Guard({ me, permission, children }: { me: Me; permission: Permission; children: ReactNode }) {
  return me.permissions.includes(permission) ? children : <Forbidden />;
}

/** Trang chủ = mục đầu tiên vai trò được xem (admin console không có số liệu Copilot). */
function Home({ me }: { me: Me }) {
  if (me.permissions.includes('ai:metrics:read')) return <OverviewPage />;
  const first = NAV_ITEMS.find((item) => me.permissions.includes(item.permission));
  if (first) return <Navigate to={first.to} replace />;
  return <EmptyState title="Tài khoản chưa có vai trò" description="Nhờ quản trị console cấp vai trò phù hợp với việc bạn làm." />;
}

export function App() {
  const me = useMe();

  if (me.isPending) return <Loading label="Đang kiểm tra phiên…" />;
  if (me.error) {
    if (me.error instanceof ApiError && me.error.status === 401) return <LoginPage />;
    return <ErrorBlock error={me.error} onRetry={() => void me.refetch()} />;
  }
  if (!me.data.mfa_done) return <MfaPage me={me.data} />;

  const user = me.data;
  return (
    <AppShell me={user}>
      <Routes>
        <Route index element={<Home me={user} />} />
        <Route path="copilot" element={<Guard me={user} permission="ai:chatlog:read"><CopilotLabPage /></Guard>} />
        <Route path="members" element={<Guard me={user} permission="ai:member:manage"><MembersPage /></Guard>} />
        <Route path="audit" element={<Guard me={user} permission="ai:audit:read"><AuditPage /></Guard>} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </AppShell>
  );
}
