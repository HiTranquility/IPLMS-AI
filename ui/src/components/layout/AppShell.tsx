import { LogOut, Moon, Sun } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import type { Me } from '@/api/types';
import { Button } from '@/components/common/Ui/button/Button';
import { useLogout } from '@/hooks/useConsole';
import { useI18n } from '@/i18n/I18nProvider';
import { applyTheme, initialTheme, type Theme } from '@/utils/theme';
import { LanguageSwitch } from './LanguageSwitch';
import { allowed, NAV_GROUPS } from './navigation';
import styles from './AppShell.module.css';

export function AppShell({ me, children }: { me: Me; children: ReactNode }) {
  const { t } = useI18n();
  const logout = useLogout();
  const [theme, setTheme] = useState<Theme>(() => initialTheme());
  const groups = NAV_GROUPS.map((group) => ({ ...group, items: group.items.filter((item) => allowed(item, me.permissions)) })).filter(
    (group) => group.items.length > 0,
  );

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    setTheme(next);
  };

  return (
    <div className={styles.shell}>
      <aside className={styles.rail}>
        <div className={styles.brand}>
          <span className={styles.brandName}>AI Console</span>
          <span className={styles.brandScope}>{t.shell.scope}</span>
        </div>
        <nav aria-label={t.shell.navLabel} className={styles.navWrap}>
          {groups.map((group) => (
            <div key={group.label} className={styles.group}>
              <p className={styles.groupLabel}>{t.nav[group.label]}</p>
              <ul className={styles.nav}>
                {group.items.map(({ to, label, icon: Icon }) => (
                  <li key={to}>
                    <NavLink to={to} end={to === '/' || to === '/vision'} className={({ isActive }) => (isActive ? `${styles.link} ${styles.active}` : styles.link)}>
                      <Icon size={16} aria-hidden />
                      {t.nav[label]}
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
          <p className={styles.roles}>{me.roles.length ? me.roles.join(', ') : t.shell.rolesNone}</p>
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
      <main className={styles.main}>{children}</main>
    </div>
  );
}
