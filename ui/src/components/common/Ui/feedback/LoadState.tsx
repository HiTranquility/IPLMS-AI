import { CircleAlert } from 'lucide-react';
import { ApiError } from '@/api/client';
import { useI18n } from '@/i18n/I18nProvider';
import { Button } from '../button/Button';
import { Spinner } from './Spinner';
import styles from './LoadState.module.css';

/** Trạng thái tải/lỗi trung thực cho mọi màn hình dữ liệu (Hallmark luật 7). */
export function Loading({ label }: { label?: string }) {
  const { t } = useI18n();
  return (
    <div className={styles.row} role="status">
      <Spinner size={16} />
      <span>{label ?? t.feedback.loading}</span>
    </div>
  );
}

export function ErrorBlock({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useI18n();
  const api = error instanceof ApiError ? error : undefined;
  // Thông điệp server viết bằng tiếng Việt: ngôn ngữ khác thì hiện câu dịch theo `code`, giữ nguyên văn bên dưới.
  const translated = api?.fromServer ? t.errors.serverCodes[api.code] : undefined;
  const message = translated ?? (error instanceof Error ? error.message : t.feedback.loadFailed);
  return (
    <div className={styles.error} role="alert">
      <CircleAlert size={18} aria-hidden />
      <div className={styles.body}>
        <p>{message}</p>
        {translated && <p className={styles.detail}>{t.feedback.serverSaid} <span lang="vi">{api!.message}</span></p>}
        {api && <p className={styles.code}>{t.feedback.code(api.code)}</p>}
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          {t.feedback.retry}
        </Button>
      )}
    </div>
  );
}
