import { Copy, ShieldCheck } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { TextField } from '@/components/common/Ui/form/Field';
import { LanguageSwitch } from '@/components/layout/LanguageSwitch';
import { useEnrollTotp, useLogout, useVerifyTotp } from '@/hooks/mutations/useAuthMutations';
import { useI18n } from '@/i18n/I18nProvider';
import type { Me } from '@/types/auth';
import { EnterpriseBackground } from './components/EnterpriseBackground';
import styles from './MfaPage.module.css';

/** Lấy secret từ otpauth URI để nhập tay (console không thêm lib QR — ít phụ thuộc, 0 CDN). */
export function secretFromUri(uri: string): string {
  try {
    return new URL(uri).searchParams.get('secret') ?? '';
  } catch {
    return '';
  }
}

const groupSecret = (secret: string) => secret.replace(/(.{4})/g, '$1 ').trim();

export interface MfaPageProps {
  me: Me;
}

export function MfaPage({ me }: MfaPageProps) {
  const { t } = useI18n();
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
      <EnterpriseBackground />
      <section className={styles.panel} aria-labelledby="mfa-title">
        <div className={styles.top}>
          <p className={styles.scope}>{t.mfa.step(me.email)}</p>
          <LanguageSwitch />
        </div>
        <h1 id="mfa-title" className={styles.title}>{needsEnroll ? t.mfa.enrollTitle : t.mfa.verifyTitle}</h1>

        {needsEnroll && !enroll.data && (
          <>
            <p className={styles.lead}>{t.mfa.enrollLead}</p>
            {enroll.error && <ErrorBlock error={enroll.error} />}
            <Button onClick={() => enroll.mutate()} loading={enroll.isPending}>
              <ShieldCheck size={16} aria-hidden />
              {t.mfa.createKey}
            </Button>
          </>
        )}

        {needsEnroll && enroll.data && (
          <div className={styles.secretBox}>
            <p className={styles.lead}>{t.mfa.manualLead}</p>
            <code className={styles.secret} aria-label={t.mfa.keyLabel}>{groupSecret(secret)}</code>
            <Button variant="ghost" size="sm" onClick={copy}>
              <Copy size={14} aria-hidden />
              {copied ? t.mfa.copied : t.mfa.copy}
            </Button>
            <p className={styles.note}>{t.mfa.keyOnce}</p>
          </div>
        )}

        {me.totp_pending && <p className={styles.lead}>{t.mfa.pendingLead}</p>}

        {(!needsEnroll || enroll.data) && (
          <form className={styles.form} onSubmit={submit}>
            <TextField
              label={t.mfa.otp}
              hint={t.mfa.otpHint}
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              maxLength={6}
              required
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
            />
            {verify.error && <ErrorBlock error={verify.error} />}
            <Button type="submit" loading={verify.isPending} disabled={code.length !== 6}>
              {t.mfa.confirm}
            </Button>
          </form>
        )}

        <Button variant="ghost" size="sm" onClick={() => logout.mutate()} loading={logout.isPending}>
          {t.mfa.otherAccount}
        </Button>
      </section>
    </div>
  );
}

export default MfaPage;
