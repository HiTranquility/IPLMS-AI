import { LogOut, Menu, Moon, Sun, X } from 'lucide-react';
import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
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
const FOCUSABLE = 'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])';

export function AppShell({ me, children }: AppShellProps) {
  const { t } = useI18n();
  const logout = useLogout();
  const { theme, toggleTheme } = useThemeStore();
  const { persona } = useWorkspaceStore();
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const railRef = useRef<HTMLElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

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

  return (
    <div className={styles.shell}>
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
        ref={railRef}
        className={drawerOpen ? `${styles.rail} ${styles.railOpen}` : styles.rail}
        onKeyDown={onRailKeyDown}
      >
        <div className={styles.brand}>
          <div className={styles.brandText}>
            <span className={styles.brandName}>AI Console</span>
            <span className={styles.brandScope}>{t.shell.scope}</span>
          </div>
          <button type="button" className={styles.closeButton} aria-label={t.shell.closeMenu} onClick={() => setDrawerOpen(false)}>
            <X size={18} aria-hidden />
          </button>
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
