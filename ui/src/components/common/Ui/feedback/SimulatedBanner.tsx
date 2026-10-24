import { FlaskConical } from 'lucide-react';
import { useI18n } from '@/i18n/I18nProvider';
import { Badge } from '../data-display/Badge';
import styles from './SimulatedBanner.module.css';

/**
 * Nhãn cố định cho công cụ chưa có API thật trên console (ai bug-018, DESIGN luật 2
 * "Không bịa số"). Không tắt được: người xem luôn biết đây không phải kết quả model.
 */
export function SimulatedBanner({ detail }: { detail?: string }) {
  const { t } = useI18n();
  return (
    <div className={styles.banner} role="note" aria-label={t.simulated.badge}>
      <FlaskConical size={14} aria-hidden />
      <Badge tone="warning">{t.simulated.badge}</Badge>
      <span>{detail ?? t.simulated.note}</span>
    </div>
  );
}
