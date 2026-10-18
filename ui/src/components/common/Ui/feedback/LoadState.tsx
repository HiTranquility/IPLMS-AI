import { CircleAlert } from 'lucide-react';
import { ApiError } from '@/api/client';
import { Button } from '../button/Button';
import { Spinner } from './Spinner';
import styles from './LoadState.module.css';

/** Trạng thái tải/lỗi trung thực cho mọi màn hình dữ liệu (Hallmark luật 7). */
export function Loading({ label = 'Đang tải…' }: { label?: string }) {
  return (
    <div className={styles.row} role="status">
      <Spinner size={16} />
      <span>{label}</span>
    </div>
  );
}

export function ErrorBlock({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : 'Không tải được dữ liệu.';
  const code = error instanceof ApiError ? error.code : undefined;
  return (
    <div className={styles.error} role="alert">
      <CircleAlert size={18} aria-hidden />
      <div className={styles.body}>
        <p>{message}</p>
        {code && <p className={styles.code}>Mã: {code}</p>}
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Thử lại
        </Button>
      )}
    </div>
  );
}
