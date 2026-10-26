import { AlertTriangle, KeyRound, LockKeyhole, Moon, ShieldCheck, Sun } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { useLocation } from 'react-router-dom';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { TextField } from '@/components/common/Ui/form/Field';
import { LanguageSwitch } from '@/components/layout/LanguageSwitch';
import { usePasswordLogin } from '@/hooks/mutations/useAuthMutations';
import { useI18n } from '@/i18n/I18nProvider';
import { AUTH_ENDPOINTS } from '@/services/apiEndpoints/auth.endpoint';
import { useThemeStore } from '@/stores/useThemeStore';
import { loginErrorMessage } from './loginErrors';
import styles from './LoginPage.module.css';

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
        fill="#EA4335"
      />
    </svg>
  );
}

export function LoginPage() {
  const { t } = useI18n();
  const { theme, toggleTheme } = useThemeStore();
  const login = usePasswordLogin();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const location = useLocation();
  const callbackError = loginErrorMessage(new URLSearchParams(window.location.search).get('login_error'), t);

  const saveReturnTo = () => {
    const searchParams = new URLSearchParams(window.location.search);
    const returnToParam = searchParams.get('return_to');
    // Đường dẫn theo router (đã bỏ basename `/console`): <Navigate> ở Home sẽ tự cộng basename (bug-033).
    const currentPath = location.pathname + location.search;
    const target = returnToParam || (!currentPath.startsWith('/auth') && location.pathname !== '/' ? currentPath : null);
    if (target && !target.startsWith('//')) {
      try {
        sessionStorage.setItem('console_return_to', target);
      } catch {
        // Storage unavailable fallback
      }
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    saveReturnTo();
    login.mutate({ email, password });
  };

  return (
    <div className={styles.page}>

      <main className={styles.container}>
        <section className={styles.panel} aria-labelledby="login-title">
          {/* Top Brand / Meta Bar */}
          <div className={styles.top}>
            <div className={styles.brandRow}>
              <div className={styles.logoBadge}>
                <ShieldCheck size={16} className={styles.logoIcon} aria-hidden />
                <span className={styles.scope}>{t.login.scope}</span>
              </div>
            </div>

            <div className={styles.controls}>
              <LanguageSwitch />
              <button
                type="button"
                className={styles.themeToggle}
                onClick={toggleTheme}
                aria-label={theme === 'dark' ? t.shell.toLight : t.shell.toDark}
                title={theme === 'dark' ? t.shell.toLight : t.shell.toDark}
              >
                {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
              </button>
            </div>
          </div>

          {/* Heading */}
          <div className={styles.header}>
            <h1 id="login-title" className={styles.title}>{t.login.title}</h1>
            <p className={styles.lead}>{t.login.lead}</p>
          </div>

          {/* Callback Alert */}
          {callbackError && (
            <div className={styles.alert} role="alert">
              <AlertTriangle size={14} className={styles.alertIcon} aria-hidden />
              <span>{callbackError}</span>
            </div>
          )}

          {/* Google Sign-In Action */}
          <div className={styles.actionBlock}>
            <a className={styles.google} href={AUTH_ENDPOINTS.GOOGLE_START} onClick={saveReturnTo}>
              <GoogleIcon />
              <span>{t.login.google}</span>
            </a>
            <div className={styles.securityHint}>
              <LockKeyhole size={13} className={styles.hintIcon} aria-hidden />
              <span>{t.login.securityHint}</span>
            </div>
          </div>

          {/* Divider */}
          <div className={styles.divider} role="separator">
            <span className={styles.dividerLine} />
            <span className={styles.dividerText}>{t.login.orEmergency}</span>
            <span className={styles.dividerLine} />
          </div>

          {/* Emergency Backup Login */}
          <details className={styles.emergency}>
            <summary>
              <KeyRound size={15} aria-hidden />
              <span>{t.login.emergency}</span>
            </summary>
            <p className={styles.note}>{t.login.emergencyNote}</p>
            <form className={styles.form} onSubmit={submit}>
              <TextField
                label={t.login.email}
                type="email"
                autoComplete="username"
                placeholder="admin@iplms.internal"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <TextField
                label={t.login.password}
                type="password"
                autoComplete="current-password"
                placeholder="••••••••••••"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              {login.error && <ErrorBlock error={login.error} />}
              <Button type="submit" loading={login.isPending}>
                {t.login.submit}
              </Button>
            </form>
          </details>

          {/* Footer Security Watermark */}
          <footer className={styles.footer}>
            <p className={styles.footerMain}>
              {t.login.footerMain}
            </p>
            <p className={styles.footerSub}>
              {t.login.footerSub}
            </p>
          </footer>
        </section>
      </main>
    </div>
  );
}

export default LoginPage;
