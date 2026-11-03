import { ChevronDown, LogOut, Menu, Moon, PanelLeftClose, PanelLeftOpen, Search, Settings, Sun } from 'lucide-react';
import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
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
import { allowed, NAV_GROUPS, PERSONA_LIST, resolvePersona } from './navigation';
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
  const { t, lang } = useI18n();
  const logout = useLogout();
  const { theme, toggleTheme } = useThemeStore();
  const { persona: savedPersona } = useWorkspaceStore(me.member_id);
  const persona = resolvePersona(me, savedPersona);
  const location = useLocation();
  const navigate = useNavigate();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [quickJumpOpen, setQuickJumpOpen] = useState(false);
  const [quickQuery, setQuickQuery] = useState('');
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
  const quickInputRef = useRef<HTMLInputElement>(null);

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

  // Chuyển trang thì đóng ngăn kéo & đóng hộp nhảy nhanh; lên màn rộng thì bỏ trạng thái mở.
  useEffect(() => {
    setDrawerOpen(false);
    setQuickJumpOpen(false);
    setQuickQuery('');
  }, [location.pathname]);

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

  // Esc đóng ngăn kéo hoặc hộp Quick Jump; Ctrl+K mở Quick Jump.
  useEffect(() => {
    const onKey = (event: globalThis.KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setQuickJumpOpen((prev) => !prev);
        return;
      }
      if (event.key === 'Escape') {
        if (quickJumpOpen) {
          event.preventDefault();
          setQuickJumpOpen(false);
        } else if (drawerOpen) {
          event.preventDefault();
          setDrawerOpen(false);
        }
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [drawerOpen, quickJumpOpen]);

  useEffect(() => {
    if (quickJumpOpen) {
      requestAnimationFrame(() => quickInputRef.current?.focus());
    }
  }, [quickJumpOpen]);

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

  const groups = useMemo(
    () =>
      NAV_GROUPS.map((group) => ({
        ...group,
        items: group.items.filter((item) => allowed(item, me.permissions, persona)),
      })).filter((group) => group.items.length > 0),
    [me.permissions, persona],
  );

  // Tìm nhóm và trang hiện tại cho Breadcrumb (C1)
  const activeCrumb = useMemo(() => {
    if (location.pathname.startsWith('/settings')) {
      return { groupLabel: t.shell.scope, pageLabel: t.nav.settings };
    }
    for (const group of NAV_GROUPS) {
      const exact = group.items.find((it) => it.to === location.pathname);
      if (exact) {
        return { groupLabel: t.nav[group.label], pageLabel: t.nav[exact.label] };
      }
    }
    for (const group of NAV_GROUPS) {
      const prefix = group.items.find((it) => it.to !== '/' && location.pathname.startsWith(it.to));
      if (prefix) {
        return { groupLabel: t.nav[group.label], pageLabel: t.nav[prefix.label] };
      }
    }
    return { groupLabel: t.nav.copilot, pageLabel: t.nav.overview };
  }, [location.pathname, t]);

  const activePersonaMeta = useMemo(
    () => PERSONA_LIST.find((p) => p.id === persona) ?? PERSONA_LIST[0],
    [persona],
  );

  const quickJumpItems = useMemo(() => {
    const q = quickQuery.trim().toLowerCase();
    const allPermitted = NAV_GROUPS.flatMap((g) =>
      g.items
        .filter((it) => allowed(it, me.permissions, 'all'))
        .map((it) => ({
          to: it.to,
          groupText: t.nav[g.label],
          labelText: t.nav[it.label],
          icon: it.icon,
        })),
    );
    if (!q) return allPermitted;
    return allPermitted.filter(
      (it) => it.labelText.toLowerCase().includes(q) || it.groupText.toLowerCase().includes(q) || it.to.toLowerCase().includes(q),
    );
  }, [me.permissions, quickQuery, t]);

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
  const canOpenSettings = allowed(
    { permissions: ['ai:metrics:read', 'ai:member:manage', 'ai:audit:read'] },
    me.permissions,
  );
  const isCompact = railCollapsed && !drawerOpen;
  const quickJumpPlaceholder = lang === 'en' ? 'Jump to page…' : 'Chuyển nhanh tới trang…';

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
        <span className={styles.mobileCrumb}>{activeCrumb.pageLabel}</span>
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
                          end={to === '/' || to === '/vision' || to === '/copilot'}
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
                {canOpenSettings && (
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
                )}
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

      <div className={styles.contentCol}>
        <div className={styles.contextBar}>
          <div className={styles.contextLeft}>
            <div className={styles.breadcrumb}>
              <span className={styles.crumbGroup}>{activeCrumb.groupLabel}</span>
              <span className={styles.crumbSep} aria-hidden>/</span>
              <span className={styles.crumbPage}>{activeCrumb.pageLabel}</span>
            </div>
            <span className={styles.contextPill}>
              <span className={styles.contextDot} aria-hidden />
              <span>{t.workspace[activePersonaMeta.titleKey]}</span>
              <span className={styles.contextBadge}>{activePersonaMeta.badge}</span>
            </span>
          </div>

          <div className={styles.contextRight}>
            <div className={styles.quickJumpWrap}>
              <button
                type="button"
                className={styles.quickJumpTrigger}
                onClick={() => setQuickJumpOpen((prev) => !prev)}
                aria-expanded={quickJumpOpen}
              >
                <Search size={13} aria-hidden />
                <span>{quickJumpPlaceholder}</span>
                <kbd className={styles.kbd}>Ctrl K</kbd>
              </button>

              {quickJumpOpen && (
                <div className={styles.quickJumpPopover}>
                  <input
                    ref={quickInputRef}
                    type="search"
                    className={styles.quickJumpInput}
                    placeholder={quickJumpPlaceholder}
                    value={quickQuery}
                    onChange={(e) => setQuickQuery(e.target.value)}
                  />
                  <ul className={styles.quickJumpList}>
                    {quickJumpItems.map((it) => {
                      const Icon = it.icon;
                      return (
                        <li key={it.to}>
                          <button
                            type="button"
                            className={styles.quickJumpItem}
                            onClick={() => {
                              navigate(it.to);
                              setQuickJumpOpen(false);
                            }}
                          >
                            <Icon size={14} aria-hidden />
                            <span className={styles.quickJumpItemLabel}>{it.labelText}</span>
                            <span className={styles.quickJumpItemGroup}>{it.groupText}</span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>

        <main className={styles.main}>
          <PageBoundary>{children ?? <Outlet />}</PageBoundary>
        </main>
      </div>
    </div>
  );
}

export default AppShell;
