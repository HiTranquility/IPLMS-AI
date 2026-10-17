import type { ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { ApiError } from '@/api/client';
import type { Me, Permission } from '@/api/types';
import { Forbidden } from '@/components/common/Shared/Forbidden';
import { NotFound } from '@/components/common/Shared/NotFound';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { AppShell } from '@/components/layout/AppShell';
import { allowed, NAV_ITEMS } from '@/components/layout/navigation';
import { useMe } from '@/hooks/useConsole';
import { useI18n } from '@/i18n/I18nProvider';
import { AuditPage } from '@/pages/Audit/AuditPage';
import { LoginPage } from '@/pages/Auth/LoginPage';
import { MfaPage } from '@/pages/Auth/MfaPage';
import { CopilotLabPage } from '@/pages/Copilot/CopilotLabPage';
import { MembersPage } from '@/pages/Members/MembersPage';
import { OverviewPage } from '@/pages/Overview/OverviewPage';
import { ToolsPage } from '@/pages/Tools/ToolsPage';
import { DatasetsPage } from '@/pages/Vision/DatasetsPage';
import { LabelPage } from '@/pages/Vision/LabelPage';
import { ModelsPage } from '@/pages/Vision/ModelsPage';
import { ReviewPage } from '@/pages/Vision/ReviewPage';
import { VisionOverviewPage } from '@/pages/Vision/VisionOverviewPage';

function Guard({ me, permission, children }: { me: Me; permission: Permission | Permission[]; children: ReactNode }) {
  const permissions = Array.isArray(permission) ? permission : [permission];
  return allowed({ permissions }, me.permissions) ? children : <Forbidden />;
}

/** Trang chủ = mục đầu tiên vai trò được xem (admin console không có số liệu Copilot). */
function Home({ me }: { me: Me }) {
  const { t } = useI18n();
  if (me.permissions.includes('ai:metrics:read')) return <OverviewPage />;
  const first = NAV_ITEMS.find((item) => allowed(item, me.permissions));
  if (first) return <Navigate to={first.to} replace />;
  return <EmptyState title={t.app.noRoleTitle} description={t.app.noRoleDesc} />;
}

export function App() {
  const { t } = useI18n();
  const me = useMe();

  if (me.isPending) return <Loading label={t.app.checkingSession} />;
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
        <Route path="tools" element={<Guard me={user} permission={['ai:metrics:read', 'ai:prompt:edit']}><ToolsPage /></Guard>} />
        <Route path="vision" element={<Guard me={user} permission="ai:metrics:read"><VisionOverviewPage /></Guard>} />
        <Route path="vision/label" element={<Guard me={user} permission="ai:task:label"><LabelPage /></Guard>} />
        <Route path="vision/review" element={<Guard me={user} permission="ai:label:approve"><ReviewPage /></Guard>} />
        <Route path="vision/datasets" element={<Guard me={user} permission={['ai:dataset:snapshot', 'ai:model:evaluate']}><DatasetsPage /></Guard>} />
        <Route path="vision/models" element={<Guard me={user} permission="ai:metrics:read"><ModelsPage /></Guard>} />
        <Route path="members" element={<Guard me={user} permission="ai:member:manage"><MembersPage /></Guard>} />
        <Route path="audit" element={<Guard me={user} permission="ai:audit:read"><AuditPage /></Guard>} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </AppShell>
  );
}
