import { KeyRound, LogIn } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { API_BASE } from '@/api/client';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { TextField } from '@/components/common/Ui/form/Field';
import { LanguageSwitch } from '@/components/layout/LanguageSwitch';
import { usePasswordLogin } from '@/hooks/useConsole';
import { useI18n } from '@/i18n/I18nProvider';
import { loginErrorMessage } from './loginErrors';
import styles from './auth.module.css';

export function LoginPage() {
  const { t } = useI18n();
  const login = usePasswordLogin();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const callbackError = loginErrorMessage(new URLSearchParams(window.location.search).get('login_error'), t);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    login.mutate({ email, password });
  };

  return (
    <div className={styles.page}>
      <section className={styles.panel} aria-labelledby="login-title">
        <div className={styles.top}>
          <p className={styles.scope}>{t.login.scope}</p>
          <LanguageSwitch />
        </div>
        <h1 id="login-title" className={styles.title}>{t.login.title}</h1>
        <p className={styles.lead}>{t.login.lead}</p>

        {callbackError && <p className={styles.alert} role="alert">{callbackError}</p>}

        {/* Điều hướng cả trang: Google phải chuyển về callback cùng nguồn để gắn cookie luồng. */}
        <a className={styles.google} href={`${API_BASE}/auth/google/start`}>
          <LogIn size={16} aria-hidden />
          {t.login.google}
        </a>

        <details className={styles.emergency}>
          <summary>
            <KeyRound size={14} aria-hidden />
            {t.login.emergency}
          </summary>
          <p className={styles.note}>{t.login.emergencyNote}</p>
          <form className={styles.form} onSubmit={submit}>
            <TextField label={t.login.email} type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
            <TextField label={t.login.password} type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
            {login.error && <ErrorBlock error={login.error} />}
            <Button type="submit" loading={login.isPending}>{t.login.submit}</Button>
          </form>
        </details>
      </section>
    </div>
  );
}
