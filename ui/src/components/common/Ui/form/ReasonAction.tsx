import { ShieldCheck } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { useI18n } from '@/i18n/I18nProvider';
import { Button, type ButtonProps } from '../button/Button';
import { ErrorBlock } from '../feedback/LoadState';
import { TextField } from './Field';
import styles from './ReasonAction.module.css';

export interface ReasonActionProps {
  label: string;
  reasonLabel?: string;
  variant?: ButtonProps['variant'];
  disabled?: boolean;
  disabledHint?: string;
  onSubmit: (reason: string) => Promise<unknown>;
  onStepUp?: (code: string, reason: string) => Promise<unknown>;
}

function isStepUpRequiredError(err: unknown): boolean {
  return (
    typeof err === 'object' &&
    err !== null &&
    'code' in err &&
    (err as { code?: unknown }).code === 'STEP_UP_REQUIRED'
  );
}

/**
 * Thao tác bắt buộc ghi lý do (UI Primitive thuần — không gọi trực tiếp apiEndpoints).
 * Nếu server trả STEP_UP_REQUIRED (quyền nhạy cảm, ADR-0048 §4), hiện ô mã TOTP
 * ngay tại chỗ và gọi `onStepUp` rồi làm tiếp.
 */
export function ReasonAction({
  label,
  reasonLabel,
  variant = 'secondary',
  disabled,
  disabledHint,
  onSubmit,
  onStepUp,
}: ReasonActionProps) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [code, setCode] = useState('');
  const [needStepUp, setNeedStepUp] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [pending, setPending] = useState(false);

  if (!open) {
    return (
      <span className={styles.trigger}>
        <Button size="sm" variant={variant} disabled={disabled} onClick={() => setOpen(true)}>
          {label}
        </Button>
        {disabled && disabledHint && <span className={styles.hint}>{disabledHint}</span>}
      </span>
    );
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      if (needStepUp && onStepUp) await onStepUp(code, reason.trim());
      await onSubmit(reason.trim());
      setOpen(false);
      setReason('');
      setCode('');
      setNeedStepUp(false);
    } catch (err) {
      if (isStepUpRequiredError(err)) setNeedStepUp(true);
      else setError(err);
    } finally {
      setPending(false);
    }
  };

  return (
    <form className={styles.form} onSubmit={submit}>
      <TextField label={reasonLabel ?? t.reasonAction.reason} required minLength={3} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
      {needStepUp && (
        <div className={styles.stepUp}>
          <p className={styles.stepUpText}>
            <ShieldCheck size={14} aria-hidden />
            {t.reasonAction.stepUp}
          </p>
          <TextField
            label={t.reasonAction.otp}
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]{6}"
            maxLength={6}
            required
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
          />
        </div>
      )}
      {error !== null && <ErrorBlock error={error} />}
      <div className={styles.actions}>
        <Button type="submit" size="sm" variant={variant === 'secondary' ? 'primary' : variant} loading={pending} disabled={reason.trim().length < 3 || (needStepUp && code.length !== 6)}>
          {needStepUp ? t.reasonAction.confirm : label}
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>{t.reasonAction.cancel}</Button>
      </div>
    </form>
  );
}

export default ReasonAction;
