import { Navigate, Route, Routes } from 'react-router-dom';
import { PermissionGuard } from '@/components/common/Guard/PermissionGuard';
import { NotFound } from '@/components/common/Shared/NotFound';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { AppShell } from '@/components/layout/AppShell';
import { allowed, NAV_ITEMS } from '@/components/layout/navigation';
import { useI18n } from '@/i18n/I18nProvider';
import { useWorkspaceStore } from '@/stores/useWorkspaceStore';
import { AuditPage } from '@/pages/Audit/AuditPage';
import { CopilotLabPage } from '@/pages/Copilot/CopilotLabPage';
import { MembersPage } from '@/pages/Members/MembersPage';
import { OverviewPage } from '@/pages/Overview/OverviewPage';
import { KnowledgePage } from '@/pages/Knowledge';
import { SettingsPage } from '@/pages/Settings/SettingsPage';
import { ToolsPage } from '@/pages/Tools/ToolsPage';
import { DatasetsPage, LabelPage, ModelsPage, ReviewPage, VisionOverviewPage } from '@/pages/Vision';
import type { Me } from '@/types/auth';

/** Trang chủ = mục đầu tiên vai trò được xem (admin console không có số liệu Copilot). */
function Home({ me }: { me: Me }) {
  const { t } = useI18n();
  const { persona } = useWorkspaceStore();

  const returnTo = typeof window !== 'undefined' ? sessionStorage.getItem('console_return_to') : null;
  if (returnTo) {
    sessionStorage.removeItem('console_return_to');
    if (returnTo.startsWith('/') && !returnTo.startsWith('//') && !returnTo.startsWith('/auth')) {
      return <Navigate to={returnTo} replace />;
    }
  }

  if (persona === 'admin' && me.permissions.includes('ai:member:manage')) {
    return <Navigate to="/members" replace />;
  }
  if (persona === 'labeling' && me.permissions.includes('ai:task:label')) {
    return <Navigate to="/vision/label" replace />;
  }
  if (persona === 'ml' && me.permissions.includes('ai:metrics:read')) {
    return <Navigate to="/vision/models" replace />;
  }
  if (me.permissions.includes('ai:metrics:read')) return <OverviewPage />;
  const first = NAV_ITEMS.find((item) => allowed(item, me.permissions, persona));
  if (first) return <Navigate to={first.to} replace />;
  return <EmptyState title={t.app.noRoleTitle} description={t.app.noRoleDesc} />;
}

export interface AuthenticatedRoutesProps {
  me: Me;
}

export function AuthenticatedRoutes({ me }: AuthenticatedRoutesProps) {
  return (
    <AppShell me={me}>
      <Routes>
        <Route index element={<Home me={me} />} />
        <Route
          path="copilot"
          element={
            <PermissionGuard me={me} permission="ai:chatlog:read">
              <CopilotLabPage initialMode="chat" />
            </PermissionGuard>
          }
        />
        <Route
          path="copilot/logs"
          element={
            <PermissionGuard me={me} permission="ai:chatlog:read">
              <CopilotLabPage initialMode="review" />
            </PermissionGuard>
          }
        />
        <Route
          path="knowledge"
          element={
            <PermissionGuard me={me} permission="ai:prompt:edit">
              <KnowledgePage />
            </PermissionGuard>
          }
        />
        <Route
          path="tools"
          element={
            <PermissionGuard me={me} permission={['ai:metrics:read', 'ai:prompt:edit']}>
              <ToolsPage />
            </PermissionGuard>
          }
        />
        <Route
          path="vision"
          element={
            <PermissionGuard me={me} permission="ai:metrics:read">
              <VisionOverviewPage />
            </PermissionGuard>
          }
        />
        <Route
          path="vision/label"
          element={
            <PermissionGuard me={me} permission="ai:task:label">
              <LabelPage />
            </PermissionGuard>
          }
        />
        <Route
          path="vision/review"
          element={
            <PermissionGuard me={me} permission="ai:label:approve">
              <ReviewPage />
            </PermissionGuard>
          }
        />
        <Route
          path="vision/datasets"
          element={
            <PermissionGuard me={me} permission={['ai:dataset:snapshot', 'ai:model:evaluate']}>
              <DatasetsPage />
            </PermissionGuard>
          }
        />
        <Route
          path="vision/models"
          element={
            <PermissionGuard me={me} permission="ai:metrics:read">
              <ModelsPage />
            </PermissionGuard>
          }
        />
        <Route
          path="members"
          element={
            <PermissionGuard me={me} permission="ai:member:manage">
              <MembersPage />
            </PermissionGuard>
          }
        />
        <Route
          path="audit"
          element={
            <PermissionGuard me={me} permission="ai:audit:read">
              <AuditPage />
            </PermissionGuard>
          }
        />
        <Route
          path="settings"
          element={
            <PermissionGuard me={me} permission={['ai:metrics:read', 'ai:member:manage', 'ai:audit:read']}>
              <SettingsPage />
            </PermissionGuard>
          }
        />
        <Route path="auth/*" element={<Navigate to="/" replace />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </AppShell>
  );
}

export default AuthenticatedRoutes;
