import { Clock, History } from 'lucide-react';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import styles from './LabelStudio.module.css';

export interface HistoryItem {
  captureId: string;
  plateText: string;
  verdict: 'CORRECT' | 'CORRECTED' | 'UNUSABLE';
  timestamp: Date;
}

interface LabelHistoryDrawerProps {
  items: HistoryItem[];
}

export function LabelHistoryDrawer({ items }: LabelHistoryDrawerProps) {
  if (items.length === 0) {
    return (
      <div className={styles.historyDrawer}>
        <div className={styles.infoCardTitle}>
          <History size={16} aria-hidden />
          Lịch sử gán nhãn trong phiên
        </div>
        <p style={{ margin: 0, fontSize: 'var(--text-xs)', color: 'var(--color-muted)' }}>
          Chưa có mẫu nào được gán nhãn trong phiên làm việc này.
        </p>
      </div>
    );
  }

  const getTone = (verdict: string) => {
    switch (verdict) {
      case 'CORRECT':
        return 'success';
      case 'CORRECTED':
        return 'accent';
      case 'UNUSABLE':
        return 'danger';
      default:
        return 'neutral';
    }
  };

  return (
    <div className={styles.historyDrawer} role="region" aria-label="Lịch sử các mẫu đã gán">
      <div className={styles.infoCardTitle}>
        <History size={16} aria-hidden />
        Lịch sử gán nhãn trong phiên ({items.length} mẫu)
      </div>

      <ul className={styles.historyList}>
        {items.map((item, idx) => (
          <li key={`${item.captureId}-${idx}`} className={styles.historyItem}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                {item.plateText || '—'}
              </span>
              <Badge tone={getTone(item.verdict)}>
                {item.verdict === 'CORRECT'
                  ? 'Đúng 100%'
                  : item.verdict === 'CORRECTED'
                  ? 'Đã sửa'
                  : 'Ảnh hỏng'}
              </Badge>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', color: 'var(--color-muted)' }}>
              <Clock size={12} aria-hidden />
              <span>{item.timestamp.toLocaleTimeString()}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default LabelHistoryDrawer;
