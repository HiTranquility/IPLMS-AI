import { CheckCheck, ClipboardCheck } from 'lucide-react';
import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/common/Ui/button/Button';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { PageHeader } from '@/components/layout/PageHeader';
import { queryKeys } from '@/constants/queryKeys';
import { useReviewQueue } from '@/hooks/queries/useVisionQueries';
import { useI18n } from '@/i18n/I18nProvider';
import { decideLabel } from '@/services/apiEndpoints/vision.endpoint';
import { ReviewRow } from './components/ReviewRow';
import styles from './ReviewPage.module.css';

export function ReviewPage() {
  const { t } = useI18n();
  const queue = useReviewQueue();
  const queryClient = useQueryClient();
  const [isBatchApproving, setIsBatchApproving] = useState(false);

  const items = queue.data || [];
  const exactMatches = items.filter(
    (item) => item.machine_plate && item.confirmed_plate && item.machine_plate === item.confirmed_plate,
  );

  const handleApproveAllExact = async () => {
    if (exactMatches.length === 0 || isBatchApproving) return;
    setIsBatchApproving(true);
    try {
      for (const item of exactMatches) {
        await decideLabel(item.label.id, 'APPROVED', 'Duyệt nhanh theo lô: Khớp 100%');
      }
      void queryClient.invalidateQueries({ queryKey: queryKeys.vision.reviewQueue() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.vision.accuracy() });
    } finally {
      setIsBatchApproving(false);
    }
  };

  return (
    <div className={styles.page}>
      <PageHeader
        title={t.review.title}
        description={t.review.desc}
      />

      {queue.isPending && <Loading />}
      {queue.error && <ErrorBlock error={queue.error} onRetry={() => void queue.refetch()} />}

      {items.length === 0 && !queue.isPending && (
        <EmptyState icon={<ClipboardCheck size={28} />} title={t.review.empty} />
      )}

      {items.length > 0 && (
        <>
          <div className={styles.toolbarCard}>
            <div className={styles.queueStats}>
              <div className={styles.statItem}>
                <span className={styles.statLabel}>Hàng đợi chờ duyệt</span>
                <span className={styles.statValue}>{items.length} mẫu</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statLabel}>Khớp 100% máy & cổng</span>
                <span className={styles.statValue} style={{ color: 'var(--color-success)' }}>
                  {exactMatches.length} mẫu
                </span>
              </div>
            </div>

            {exactMatches.length > 0 && (
              <Button
                variant="secondary"
                size="sm"
                loading={isBatchApproving}
                onClick={handleApproveAllExact}
                title={`Duyệt nhanh ${exactMatches.length} mẫu khớp 100%`}
              >
                <CheckCheck size={14} aria-hidden />
                Duyệt nhanh {exactMatches.length} mẫu khớp 100%
              </Button>
            )}
          </div>

          <ul className={styles.reviewList} aria-label={t.review.listLabel}>
            {items.map((item) => (
              <ReviewRow key={item.label.id} item={item} />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export default ReviewPage;
