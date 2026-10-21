import { Stat } from '@/components/common/Ui/data-display/Stat';
import { useI18n } from '@/i18n/I18nProvider';
import type { ReviewStats } from '@/types/copilot';
import { fmtInt, fmtPercent } from '@/utils/format';
import styles from '../OverviewPage.module.css';

export interface AccuracySectionProps {
  stats: ReviewStats;
}

export function AccuracySection({ stats }: AccuracySectionProps) {
  const { t } = useI18n();
  return (
    <dl className={styles.stats}>
      <Stat
        label={t.overview.accuracy}
        value={fmtPercent(stats.accuracy)}
        hint={stats.reviewed ? t.overview.reviewedHint(fmtInt(stats.reviewed)) : t.overview.noReviews}
      />
      <Stat label={t.overview.correct} value={fmtInt(stats.correct)} />
      <Stat label={t.overview.incorrect} value={fmtInt(stats.incorrect)} />
      <Stat label={t.overview.unsafe} value={fmtInt(stats.unsafe)} />
    </dl>
  );
}

export default AccuracySection;
