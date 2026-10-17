import { Copy, ShieldCheck } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import type { Me } from '@/api/types';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { TextField } from '@/components/common/Ui/form/Field';
import { useEnrollTotp, useLogout, useVerifyTotp } from '@/hooks/useConsole';
import styles from './auth.module.css';

/** Lấy secret từ otpauth URI để nhập tay (console không thêm lib QR — ít phụ thuộc, 0 CDN). */
export function secretFromUri(uri: string): string {
  try {
    return new URL(uri).searchParams.get('secret') ?? '';
  } catch {
    return '';
  }
}

const groupSecret = (secret: string) => secret.replace(/(.{4})/g, '$1 ').trim();

export function MfaPage({ me }: { me: Me }) {
  const enroll = useEnrollTotp();
  const verify = useVerifyTotp();
  const logout = useLogout();
  const [code, setCode] = useState('');
  const [copied, setCopied] = useState(false);
  const secret = enroll.data ? secretFromUri(enroll.data.otpauth_uri) : '';
  // Khoá đã tạo sẵn (admin khẩn cấp từ CLI) thì chỉ nhập mã: tạo khoá mới sẽ ghi đè khoá đã quét.
  const needsEnroll = !me.totp_enabled && !me.totp_pending;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    verify.mutate(code);
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(secret);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className={styles.page}>
      <section className={styles.panel} aria-labelledby="mfa-title">
        <p className={styles.scope}>Bước 2/2 · {me.email}</p>
        <h1 id="mfa-title" className={styles.title}>{needsEnroll ? 'Bật xác thực hai lớp' : 'Nhập mã xác thực'}</h1>

        {needsEnroll && !enroll.data && (
          <>
            <p className={styles.lead}>Console bắt buộc TOTP. Tạo khoá rồi nhập vào ứng dụng xác thực (Google Authenticator, 1Password, Aegis…).</p>
            {enroll.error && <ErrorBlock error={enroll.error} />}
            <Button onClick={() => enroll.mutate()} loading={enroll.isPending}>
              <ShieldCheck size={16} aria-hidden />
              Tạo khoá TOTP
            </Button>
          </>
        )}

        {needsEnroll && enroll.data && (
          <div className={styles.secretBox}>
            <p className={styles.lead}>Trong ứng dụng xác thực chọn “Nhập khoá thủ công”, loại theo thời gian, rồi dán khoá:</p>
            <code className={styles.secret} aria-label="Khoá TOTP">{groupSecret(secret)}</code>
            <Button variant="secondary" size="sm" onClick={copy}>
              <Copy size={14} aria-hidden />
              {copied ? 'Đã chép' : 'Chép khoá'}
            </Button>
            <p className={styles.note}>Khoá chỉ hiện lần này. Rời trang trước khi nhập mã thì phải nhờ quản trị console đặt lại.</p>
          </div>
        )}

        {me.totp_pending && <p className={styles.lead}>Nhập mã từ khoá đã thêm vào ứng dụng xác thực khi tài khoản được tạo.</p>}

        {(!needsEnroll || enroll.data) && (
          <form className={styles.form} onSubmit={submit}>
            <TextField
              label="Mã 6 số"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              maxLength={6}
              required
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
            />
            {verify.error && <ErrorBlock error={verify.error} />}
            <Button type="submit" loading={verify.isPending} disabled={code.length !== 6}>Xác nhận</Button>
          </form>
        )}

        <Button variant="ghost" size="sm" onClick={() => logout.mutate()}>Dùng tài khoản khác</Button>
      </section>
    </div>
  );
}
