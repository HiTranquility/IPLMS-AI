import { Clock, History } from 'lucide-react';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { useI18n } from '@/i18n/I18nProvider';
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
  const { t } = useI18n();
  const s = t.label.studio;
  if (items.length === 0) {
    return (
      <div className={styles.historyDrawer}>
        <div className={styles.infoCardTitle}>
          <History size={16} aria-hidden />
          {s.historyTitle}
        </div>
        <p style={{ margin: 0, fontSize: 'var(--text-xs)', color: 'var(--color-muted)' }}>
          {s.historyEmpty}
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
    <div className={styles.historyDrawer} role="region" aria-label={s.historyRegion}>
      <div className={styles.infoCardTitle}>
        <History size={16} aria-hidden />
        {s.historyCount(items.length)}
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
                  ? s.verdictCorrect
                  : item.verdict === 'CORRECTED'
                  ? s.verdictCorrected
                  : s.verdictUnusable}
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
