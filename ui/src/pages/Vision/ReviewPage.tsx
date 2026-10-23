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
            description="Không còn nhãn nào đang chờ duyệt bốn mắt trong hàng đợi. Bạn có thể nạp thêm mẫu kiểm toán thực hành để kiểm thử thao tác duyệt và từ chối."
          />
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <Button
              variant="accent"
              loading={seedMutation.isPending}
              onClick={handleSeed}
              title="Nạp mẫu kiểm toán thực hành gồm các trường hợp gán đúng và đã sửa"
            >
              <Sparkles size={14} aria-hidden />
              Nạp mẫu kiểm toán thực hành (Seed Demo Batch)
            </Button>
          </div>
        </div>
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
              <div className={styles.statItem}>
                <span className={styles.statLabel}>Đã sửa biển số</span>
                <span className={styles.statValue} style={{ color: 'var(--color-accent)' }}>
                  {correctedItems.length} mẫu
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
                  Tất cả ({items.length})
                </Button>
                <Button
                  variant={filterMode === 'EXACT' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setFilterMode('EXACT')}
                >
                  Khớp 100% ({exactMatches.length})
                </Button>
                <Button
                  variant={filterMode === 'CORRECTED' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setFilterMode('CORRECTED')}
                >
                  Đã sửa ({correctedItems.length})
                </Button>
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

              <Button
                variant="ghost"
                size="sm"
                onClick={handleSeed}
                loading={seedMutation.isPending}
                title="Nạp thêm mẫu kiểm toán"
              >
                <Sparkles size={14} aria-hidden />
              </Button>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => void queue.refetch()}
                loading={queue.isFetching}
                title="Làm mới hàng đợi"
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
