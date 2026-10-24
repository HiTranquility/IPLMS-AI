import { History, RefreshCw, Sparkles } from 'lucide-react';
import { Button } from '@/components/common/Ui/button/Button';
import { useSeedDemoBatch } from '@/hooks/mutations/useVisionMutations';
import { useI18n } from '@/i18n/I18nProvider';
import styles from './LabelStudio.module.css';

interface LabelMetricsStripProps {
  queueCount: number;
  sessionCount: number;
  avgVelocitySeconds: number;
  onRefresh: () => void;
  isRefreshing: boolean;
  onToggleHistory?: () => void;
  showHistory?: boolean;
}

export function LabelMetricsStrip({
  queueCount,
  sessionCount,
  avgVelocitySeconds,
  onRefresh,
  isRefreshing,
  onToggleHistory,
  showHistory,
}: LabelMetricsStripProps) {
  const { t } = useI18n();
  const s = t.label.studio;
  const seedMutation = useSeedDemoBatch();

  const handleSeed = () => {
    seedMutation.mutate(undefined, {
      onSuccess: () => {
        onRefresh();
      },
    });
  };

  return (
    <div className={styles.metricsStrip} role="region" aria-label={s.metricsRegion}>
      <div className={styles.metricsGroup}>
        <div className={styles.metricItem}>
          <span className={styles.metricLabel}>{s.metricQueue}</span>
          <span className={styles.metricValue}>
            {queueCount} <span className={styles.metricSub}>{s.unitSamples}</span>
          </span>
        </div>

        <div className={styles.metricItem}>
          <span className={styles.metricLabel}>{s.metricSession}</span>
          <span className={styles.metricValue}>
            {sessionCount} <span className={styles.metricSub}>{s.unitSamples}</span>
          </span>
        </div>

        <div className={styles.metricItem}>
          <span className={styles.metricLabel}>{s.metricVelocity}</span>
          <span className={styles.metricValue}>
            {avgVelocitySeconds > 0 ? `~${avgVelocitySeconds}s` : '—'} <span className={styles.metricSub}>{s.unitPerSample}</span>
          </span>
        </div>
      </div>

      <div className={styles.stripActions}>
        <Button
          variant="secondary"
          size="sm"
          onClick={handleSeed}
          loading={seedMutation.isPending}
          title={s.seedTitle}
        >
          <Sparkles size={14} aria-hidden />
          {s.seedShort}
        </Button>

        {onToggleHistory && (
          <Button
            variant={showHistory ? 'accent' : 'secondary'}
            size="sm"
            onClick={onToggleHistory}
            title={s.historyToggleTitle}
          >
            <History size={14} aria-hidden />
            {s.historyToggle(sessionCount)}
          </Button>
        )}

        <Button
          variant="secondary"
          size="sm"
          onClick={onRefresh}
          loading={isRefreshing}
          title={s.refreshQueue}
          aria-label={s.refreshQueue}
        >
          <RefreshCw size={14} aria-hidden />
        </Button>
      </div>
    </div>
  );
}

export default LabelMetricsStrip;
