import { LogOut, Moon, Sun } from 'lucide-react';
import { type ReactNode } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { PageBoundary } from '@/components/common/Boundary/PageBoundary';
import { ScrollToTop } from '@/components/common/System/ScrollToTop';
import { Button } from '@/components/common/Ui/button/Button';
import { useLogout } from '@/hooks/mutations/useAuthMutations';
import { useI18n } from '@/i18n/I18nProvider';
import { useThemeStore } from '@/stores/useThemeStore';
import { useWorkspaceStore } from '@/stores/useWorkspaceStore';
import type { Me } from '@/types/auth';
import { LanguageSwitch } from './LanguageSwitch';
import { PersonaSwitcher } from './PersonaSwitcher';
import { allowed, NAV_GROUPS } from './navigation';
import styles from './AppShell.module.css';

export interface AppShellProps {
  me: Me;
  children?: ReactNode;
}

export function AppShell({ me, children }: AppShellProps) {
  const { t } = useI18n();
  const logout = useLogout();
  const { theme, toggleTheme } = useThemeStore();
  const { persona } = useWorkspaceStore();

  const groups = NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => allowed(item, me.permissions, persona)),
  })).filter((group) => group.items.length > 0);

  const formatUserRoles = () => {
    if (!me.roles.length) return t.shell.rolesNone;
    const clean = me.roles.map((r) => r.replace(/^ai_/, ''));
    if (clean.includes('lead') && clean.length >= 4) {
      return 'lead (toàn quyền)';
    }
    if (clean.length > 3) {
      return `${clean.slice(0, 2).join(', ')} (+${clean.length - 2})`;
    }
    return clean.join(', ');
  };

  return (
    <div className={styles.shell}>
      <ScrollToTop />
      <aside className={styles.rail}>
        <div className={styles.brand}>
          <span className={styles.brandName}>AI Console</span>
          <span className={styles.brandScope}>{t.shell.scope}</span>
        </div>

        <PersonaSwitcher me={me} />

        <nav aria-label={t.shell.navLabel} className={styles.navWrap}>
          {groups.map((group) => (
            <div key={group.label} className={styles.group}>
              <p className={styles.groupLabel}>{t.nav[group.label]}</p>
              <ul className={styles.nav}>
                {group.items.map(({ to, label, icon: Icon }) => (
                  <li key={to}>
                    <NavLink
                      to={to}
                      end={to === '/' || to === '/vision'}
                      className={({ isActive }) => (isActive ? `${styles.link} ${styles.active}` : styles.link)}
                      title={t.nav[label]}
                    >
                      <Icon size={16} aria-hidden />
                      <span className={styles.linkLabel}>{t.nav[label]}</span>
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
        {groups.length === 0 && <p className={styles.noRole}>{t.shell.noRole}</p>}
        <div className={styles.account}>
          <p className={styles.name}>{me.display_name}</p>
          <p className={styles.email}>{me.email}</p>
          <p className={styles.roles} title={me.roles.map((r) => r.replace(/^ai_/, '')).join(', ')}>
            {formatUserRoles()}
          </p>
          <div className={styles.accountActions}>
            <LanguageSwitch />
            <Button variant="ghost" size="sm" onClick={toggleTheme} aria-label={theme === 'dark' ? t.shell.toLight : t.shell.toDark}>
              {theme === 'dark' ? <Sun size={14} aria-hidden /> : <Moon size={14} aria-hidden />}
            </Button>
            <Button variant="ghost" size="sm" loading={logout.isPending} onClick={() => logout.mutate()}>
              <LogOut size={14} aria-hidden />
              {t.shell.logout}
            </Button>
          </div>
        </div>
      </aside>
      <main className={styles.main}>
        <PageBoundary>{children ?? <Outlet />}</PageBoundary>
      </main>
    </div>
  );
}

export default AppShell;
