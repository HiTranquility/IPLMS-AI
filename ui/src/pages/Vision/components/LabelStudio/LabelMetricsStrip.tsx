import { History, RefreshCw, Sparkles } from 'lucide-react';
import { Button } from '@/components/common/Ui/button/Button';
import { useSeedDemoBatch } from '@/hooks/mutations/useVisionMutations';
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
  const seedMutation = useSeedDemoBatch();

  const handleSeed = () => {
    seedMutation.mutate(undefined, {
      onSuccess: () => {
        onRefresh();
      },
    });
  };

  return (
    <div className={styles.metricsStrip} role="region" aria-label="Năng suất phiên gán nhãn">
      <div className={styles.metricsGroup}>
        <div className={styles.metricItem}>
          <span className={styles.metricLabel}>Hàng đợi A2</span>
          <span className={styles.metricValue}>
            {queueCount} <span className={styles.metricSub}>mẫu</span>
          </span>
        </div>

        <div className={styles.metricItem}>
          <span className={styles.metricLabel}>Đã gán phiên này</span>
          <span className={styles.metricValue}>
            {sessionCount} <span className={styles.metricSub}>mẫu</span>
          </span>
        </div>

        <div className={styles.metricItem}>
          <span className={styles.metricLabel}>Tốc độ trung bình</span>
          <span className={styles.metricValue}>
            {avgVelocitySeconds > 0 ? `~${avgVelocitySeconds}s` : '—'} <span className={styles.metricSub}>/ mẫu</span>
          </span>
        </div>
      </div>

      <div className={styles.stripActions}>
        <Button
          variant="secondary"
          size="sm"
          onClick={handleSeed}
          loading={seedMutation.isPending}
          title="Nạp 5 mẫu biển số thực hành đa dạng (xe con, xe máy 2 dòng, taxi vàng, xe điện, biển mờ)"
        >
          <Sparkles size={14} aria-hidden />
          Nạp 5 mẫu thực hành
        </Button>

        {onToggleHistory && (
          <Button
            variant={showHistory ? 'accent' : 'secondary'}
            size="sm"
            onClick={onToggleHistory}
            title="Bật/tắt lịch sử các mẫu đã gán trong phiên"
          >
            <History size={14} aria-hidden />
            Lịch sử ({sessionCount})
          </Button>
        )}

        <Button
          variant="secondary"
          size="sm"
          onClick={onRefresh}
          loading={isRefreshing}
          title="Làm mới hàng đợi"
          aria-label="Làm mới hàng đợi"
        >
          <RefreshCw size={14} aria-hidden />
        </Button>
      </div>
    </div>
  );
}

export default LabelMetricsStrip;
