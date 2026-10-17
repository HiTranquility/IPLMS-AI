import { KeyRound, LogIn } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { API_BASE } from '@/api/client';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { TextField } from '@/components/common/Ui/form/Field';
import { usePasswordLogin } from '@/hooks/useConsole';
import { loginErrorMessage } from './loginErrors';
import styles from './auth.module.css';

export function LoginPage() {
  const login = usePasswordLogin();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const callbackError = loginErrorMessage(new URLSearchParams(window.location.search).get('login_error'));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    login.mutate({ email, password });
  };

  return (
    <div className={styles.page}>
      <section className={styles.panel} aria-labelledby="login-title">
        <p className={styles.scope}>IPLMS · Bộ phận AI · Nội bộ</p>
        <h1 id="login-title" className={styles.title}>Đăng nhập AI Console</h1>
        <p className={styles.lead}>Chỉ thành viên đã được mời. Sau Google bạn sẽ nhập mã từ ứng dụng xác thực.</p>

        {callbackError && <p className={styles.alert} role="alert">{callbackError}</p>}

        {/* Điều hướng cả trang: Google phải chuyển về callback cùng nguồn để gắn cookie luồng. */}
        <a className={styles.google} href={`${API_BASE}/auth/google/start`}>
          <LogIn size={16} aria-hidden />
          Đăng nhập bằng Google
        </a>

        <details className={styles.emergency}>
          <summary>
            <KeyRound size={14} aria-hidden />
            Tài khoản khẩn cấp
          </summary>
          <p className={styles.note}>Chỉ dùng khi Google không dùng được. Mỗi lần đăng nhập đều ghi vào nhật ký.</p>
          <form className={styles.form} onSubmit={submit}>
            <TextField label="Email" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
            <TextField label="Mật khẩu" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
            {login.error && <ErrorBlock error={login.error} />}
            <Button type="submit" loading={login.isPending}>Tiếp tục</Button>
          </form>
        </details>
      </section>
    </div>
  );
}
