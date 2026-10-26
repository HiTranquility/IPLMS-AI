import { ChevronDown, LogOut, Menu, Moon, PanelLeftClose, PanelLeftOpen, Settings, Sun } from 'lucide-react';
import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
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

// Dưới mốc này rail thành ngăn kéo (SUGGESTION-003); khớp @media trong AppShell.module.css.
const DRAWER_QUERY = '(max-width: 767px)';
const RAIL_COLLAPSED_KEY = 'iplms_rail_collapsed';
const FOCUSABLE = 'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])';

export function AppShell({ me, children }: AppShellProps) {
  const { t } = useI18n();
  const logout = useLogout();
  const { theme, toggleTheme } = useThemeStore();
  const { persona } = useWorkspaceStore();
  const location = useLocation();
  const navigate = useNavigate();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [railCollapsed, setRailCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(RAIL_COLLAPSED_KEY) === 'true';
    } catch {
      return false;
    }
  });
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});
  const railRef = useRef<HTMLElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  const toggleRailCollapsed = () => {
    setRailCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(RAIL_COLLAPSED_KEY, String(next));
      } catch {
        // Ignore storage errors
      }
      return next;
    });
  };

  const toggleGroup = (groupKey: string) => {
    setCollapsedGroups((prev) => ({ ...prev, [groupKey]: !prev[groupKey] }));
  };

  // Chuyển trang thì đóng ngăn kéo; lên màn rộng thì bỏ trạng thái mở.
  useEffect(() => setDrawerOpen(false), [location.pathname]);
  useEffect(() => {
    const mq = window.matchMedia?.(DRAWER_QUERY);
    if (!mq) return;
    const onChange = () => {
      if (!mq.matches) setDrawerOpen(false);
    };
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);
  // Mở: đưa focus vào ngăn kéo. Đóng: trả focus về nút menu (chỉ khi nút đang hiện).
  // Đặt focus ở khung hình sau: lúc effect chạy, rail có thể chưa hết visibility: hidden.
  const wasOpen = useRef(false);
  useEffect(() => {
    let frame = 0;
    if (drawerOpen) {
      frame = requestAnimationFrame(() => railRef.current?.querySelector<HTMLElement>(FOCUSABLE)?.focus());
    } else if (wasOpen.current) {
      menuButtonRef.current?.focus();
    }
    wasOpen.current = drawerOpen;
    return () => cancelAnimationFrame(frame);
  }, [drawerOpen]);

  // Esc đóng ở bất kỳ đâu khi ngăn kéo mở (kể cả khi focus chưa vào được ngăn kéo).
  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setDrawerOpen(false);
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [drawerOpen]);

  // Tab vòng trong ngăn kéo khi đang mở (focus trap).
  const onRailKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (!drawerOpen || event.key !== 'Tab' || !railRef.current) return;
    const items = [...railRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)].filter((el) => el.offsetParent !== null);
    if (items.length === 0) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const groups = NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => allowed(item, me.permissions, persona)),
  })).filter((group) => group.items.length > 0);

  const formatUserRoles = () => {
    if (!me.roles.length) return t.shell.rolesNone;
    const clean = me.roles.map((r) => r.replace(/^ai_/, ''));
    if (clean.includes('lead') && clean.length >= 4) {
      return t.shell.rolesLeadAll;
    }
    if (clean.length > 3) {
      return `${clean.slice(0, 2).join(', ')} (+${clean.length - 2})`;
    }
    return clean.join(', ');
  };

  const isSettingsActive = location.pathname.startsWith('/settings');
  const isCompact = railCollapsed && !drawerOpen;

  return (
    <div className={isCompact ? `${styles.shell} ${styles.shellCollapsed}` : styles.shell}>
      <ScrollToTop />
      <header className={styles.topbar}>
        <button
          ref={menuButtonRef}
          type="button"
          className={styles.menuButton}
          aria-label={t.shell.openMenu}
          aria-expanded={drawerOpen}
          aria-controls="console-rail"
          onClick={() => setDrawerOpen(true)}
        >
          <Menu size={18} aria-hidden />
        </button>
        <span className={styles.brandName}>AI Console</span>
      </header>
      {drawerOpen && (
        <button type="button" className={styles.scrim} aria-label={t.shell.closeMenu} tabIndex={-1} onClick={() => setDrawerOpen(false)} />
      )}
      <aside
        id="console-rail"
        aria-label={t.shell.railLabel}
        ref={railRef}
        className={[
          styles.rail,
          drawerOpen ? styles.railOpen : '',
          isCompact ? styles.railCollapsed : '',
        ].filter(Boolean).join(' ')}
        onKeyDown={onRailKeyDown}
      >
        <div className={styles.brand}>
          {!isCompact && (
            <div className={styles.brandText}>
              <span className={styles.brandName}>AI Console</span>
              <span className={styles.brandScope}>{t.shell.scope}</span>
            </div>
          )}
          <button
            type="button"
            className={styles.collapseButton}
            aria-label={t.workspace.toggleFocus}
            aria-expanded={!railCollapsed}
            title={t.workspace.toggleFocus}
            onClick={toggleRailCollapsed}
          >
            {isCompact ? <PanelLeftOpen size={16} aria-hidden /> : <PanelLeftClose size={16} aria-hidden />}
          </button>
        </div>

        <PersonaSwitcher me={me} collapsed={isCompact} />

        <nav aria-label={t.shell.navLabel} className={styles.navWrap}>
          {groups.map((group) => {
            const isGroupFolded = !isCompact && Boolean(collapsedGroups[group.label]);
            return (
              <div key={group.label} className={styles.group}>
                {!isCompact && (
                  <button
                    type="button"
                    className={styles.groupHeaderButton}
                    onClick={() => toggleGroup(group.label)}
                    aria-expanded={!isGroupFolded}
                  >
                    <span className={styles.groupLabel}>{t.nav[group.label]}</span>
                    <ChevronDown
                      size={12}
                      className={isGroupFolded ? `${styles.groupChevron} ${styles.groupChevronFolded}` : styles.groupChevron}
                      aria-hidden
                    />
                  </button>
                )}
                {!isGroupFolded && (
                  <ul className={styles.nav}>
                    {group.items.map(({ to, label, icon: Icon }) => (
                      <li key={to}>
                        <NavLink
                          to={to}
                          end={to === '/' || to === '/vision'}
                          className={({ isActive }) =>
                            [
                              styles.link,
                              isActive ? styles.active : '',
                              isCompact ? styles.linkCollapsed : '',
                            ].filter(Boolean).join(' ')
                          }
                          title={t.nav[label]}
                        >
                          <Icon size={16} aria-hidden />
                          {!isCompact && <span className={styles.linkLabel}>{t.nav[label]}</span>}
                        </NavLink>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </nav>
        {groups.length === 0 && !isCompact && <p className={styles.noRole}>{t.shell.noRole}</p>}
        <div className={isCompact ? `${styles.account} ${styles.accountCollapsed}` : styles.account}>
          {!isCompact && (
            <div className={styles.accountMeta}>
              <p className={styles.name} title={me.display_name}>{me.display_name}</p>
              <p className={styles.email} title={me.email}>{me.email}</p>
              <p className={styles.roles} title={me.roles.map((r) => r.replace(/^ai_/, '')).join(', ')}>
                {formatUserRoles()}
              </p>
            </div>
          )}
          <div className={isCompact ? `${styles.accountActions} ${styles.accountActionsCollapsed}` : styles.accountActions}>
            <div className={isCompact ? styles.accountToolbarCollapsed : styles.accountToolbar}>
              {!isCompact && <LanguageSwitch />}
              <div className={isCompact ? styles.accountQuickIconsCollapsed : styles.accountQuickIcons}>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={toggleTheme}
                  aria-label={theme === 'dark' ? t.shell.toLight : t.shell.toDark}
                  title={theme === 'dark' ? t.shell.toLight : t.shell.toDark}
                >
                  {theme === 'dark' ? <Sun size={14} aria-hidden /> : <Moon size={14} aria-hidden />}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className={isSettingsActive ? styles.settingsButtonActive : undefined}
                  onClick={() => navigate('/settings')}
                  aria-label={t.nav.settings}
                  title={t.nav.settings}
                >
                  <Settings size={14} aria-hidden />
                </Button>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className={isCompact ? styles.logoutButtonCollapsed : styles.logoutButton}
              loading={logout.isPending}
              onClick={() => logout.mutate()}
              aria-label={t.shell.logout}
              title={t.shell.logout}
            >
              <LogOut size={14} aria-hidden />
              {!isCompact && <span>{t.shell.logout}</span>}
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
