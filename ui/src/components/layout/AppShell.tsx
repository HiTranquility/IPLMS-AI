import { LogOut, Moon, Sun } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import type { Me } from '@/api/types';
import { Button } from '@/components/common/Ui/button/Button';
import { useLogout } from '@/hooks/useConsole';
import { applyTheme, initialTheme, type Theme } from '@/utils/theme';
import { NAV_ITEMS } from './navigation';
import styles from './AppShell.module.css';

export function AppShell({ me, children }: { me: Me; children: ReactNode }) {
  const logout = useLogout();
  const [theme, setTheme] = useState<Theme>(() => initialTheme());
  const items = NAV_ITEMS.filter((item) => me.permissions.includes(item.permission));

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
          <span className={styles.brandScope}>Nội bộ · IPLMS</span>
        </div>
        <nav aria-label="Mục chính">
          <ul className={styles.nav}>
            {items.map(({ to, label, icon: Icon }) => (
              <li key={to}>
                <NavLink to={to} end={to === '/'} className={({ isActive }) => (isActive ? `${styles.link} ${styles.active}` : styles.link)}>
                  <Icon size={16} aria-hidden />
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        {items.length === 0 && <p className={styles.noRole}>Chưa có vai trò nào. Nhờ quản trị console cấp vai trò.</p>}
        <div className={styles.account}>
          <p className={styles.name}>{me.display_name}</p>
          <p className={styles.email}>{me.email}</p>
          <p className={styles.roles}>{me.roles.length ? me.roles.join(', ') : 'chưa có vai trò'}</p>
          <div className={styles.accountActions}>
            <Button variant="ghost" size="sm" onClick={toggleTheme} aria-label={theme === 'dark' ? 'Chuyển giao diện sáng' : 'Chuyển giao diện tối'}>
              {theme === 'dark' ? <Sun size={14} aria-hidden /> : <Moon size={14} aria-hidden />}
            </Button>
            <Button variant="ghost" size="sm" loading={logout.isPending} onClick={() => logout.mutate()}>
              <LogOut size={14} aria-hidden />
              Đăng xuất
            </Button>
          </div>
        </div>
      </aside>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
