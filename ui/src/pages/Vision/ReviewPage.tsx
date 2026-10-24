import { CheckCheck, ClipboardCheck, RefreshCw, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/common/Ui/button/Button';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { PageHeader } from '@/components/layout/PageHeader';
import { queryKeys } from '@/constants/queryKeys';
import { useSeedDemoBatch } from '@/hooks/mutations/useVisionMutations';
import { useReviewQueue } from '@/hooks/queries/useVisionQueries';
import { useI18n } from '@/i18n/I18nProvider';
import { decideLabel } from '@/services/apiEndpoints/vision.endpoint';
import { ReviewRow } from './components/ReviewRow';
import styles from './ReviewPage.module.css';

export function ReviewPage() {
  const { t } = useI18n();
  const queue = useReviewQueue();
  const queryClient = useQueryClient();
  const seedMutation = useSeedDemoBatch();
  const [isBatchApproving, setIsBatchApproving] = useState(false);
  const [filterMode, setFilterMode] = useState<'ALL' | 'EXACT' | 'CORRECTED'>('ALL');

  const items = queue.data || [];
  const exactMatches = items.filter(
    (item) => item.machine_plate && item.confirmed_plate && item.machine_plate === item.confirmed_plate,
  );
  const correctedItems = items.filter((item) => item.label.verdict === 'CORRECTED');

  const filteredItems = items.filter((item) => {
    if (filterMode === 'EXACT') {
      return item.machine_plate && item.confirmed_plate && item.machine_plate === item.confirmed_plate;
    }
    if (filterMode === 'CORRECTED') {
      return item.label.verdict === 'CORRECTED';
    }
    return true;
  });

  const handleApproveAllExact = async () => {
    if (exactMatches.length === 0 || isBatchApproving) return;
    setIsBatchApproving(true);
    try {
      for (const item of exactMatches) {
        // Lý do ghi vào nhật ký kiểm toán phía server (tiếng Việt như mọi lý do khác), không phải chữ hiển thị.
        await decideLabel(item.label.id, 'APPROVED', 'Duyệt nhanh theo lô: Khớp 100%');
      }
      void queryClient.invalidateQueries({ queryKey: queryKeys.vision.reviewQueue() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.vision.accuracy() });
    } finally {
      setIsBatchApproving(false);
    }
  };

  const handleSeed = () => {
    seedMutation.mutate(undefined, {
      onSuccess: () => {
        void queue.refetch();
      },
    });
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
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <EmptyState
            icon={<ClipboardCheck size={28} />}
            title={t.review.empty}
            description={t.review.emptyDesc}
          />
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <Button
              variant="accent"
              loading={seedMutation.isPending}
              onClick={handleSeed}
              title={t.review.seedTitle}
            >
              <Sparkles size={14} aria-hidden />
              {t.review.seed}
            </Button>
          </div>
        </div>
      )}

      {items.length > 0 && (
        <>
          <div className={styles.toolbarCard}>
            <div className={styles.queueStats}>
              <div className={styles.statItem}>
                <span className={styles.statLabel}>{t.review.statPending}</span>
                <span className={styles.statValue}>{t.review.samples(items.length)}</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statLabel}>{t.review.statExact}</span>
                <span className={styles.statValue} style={{ color: 'var(--color-success)' }}>
                  {t.review.samples(exactMatches.length)}
                </span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statLabel}>{t.review.statCorrected}</span>
                <span className={styles.statValue} style={{ color: 'var(--color-accent-dark)' }}>
                  {t.review.samples(correctedItems.length)}
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
              {/* Filter buttons */}
              <div style={{ display: 'flex', gap: '4px', background: 'var(--color-surface-hover)', padding: '2px', borderRadius: 'var(--radius-md)' }}>
                <Button
                  variant={filterMode === 'ALL' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setFilterMode('ALL')}
                >
                  {t.review.filterAll(items.length)}
                </Button>
                <Button
                  variant={filterMode === 'EXACT' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setFilterMode('EXACT')}
                >
                  {t.review.filterExact(exactMatches.length)}
                </Button>
                <Button
                  variant={filterMode === 'CORRECTED' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setFilterMode('CORRECTED')}
                >
                  {t.review.filterCorrected(correctedItems.length)}
                </Button>
              </div>

              {exactMatches.length > 0 && (
                <Button
                  variant="secondary"
                  size="sm"
                  loading={isBatchApproving}
                  onClick={handleApproveAllExact}
                  title={t.review.approveExact(exactMatches.length)}
                >
                  <CheckCheck size={14} aria-hidden />
                  {t.review.approveExact(exactMatches.length)}
                </Button>
              )}

              <Button
                variant="ghost"
                size="sm"
                onClick={handleSeed}
                loading={seedMutation.isPending}
                title={t.review.seedMore}
                aria-label={t.review.seedMore}
              >
                <Sparkles size={14} aria-hidden />
              </Button>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => void queue.refetch()}
                loading={queue.isFetching}
                title={t.review.refresh}
                aria-label={t.review.refresh}
              >
                <RefreshCw size={14} aria-hidden />
              </Button>
            </div>
          </div>

          <ul className={styles.reviewList} aria-label={t.review.listLabel}>
            {filteredItems.map((item) => (
              <ReviewRow key={item.label.id} item={item} />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export default ReviewPage;
