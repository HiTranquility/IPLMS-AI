import { CheckCheck, ClipboardCheck, RefreshCw, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/common/Ui/button/Button';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { PageHeader } from '@/components/layout/PageHeader';
import { queryKeys } from '@/constants/queryKeys';
import { useCan } from '@/hooks/common/useCan';
import { useSeedDemoBatch } from '@/hooks/mutations/useVisionMutations';
import { useReviewQueue } from '@/hooks/queries/useVisionQueries';
import { useI18n } from '@/i18n/I18nProvider';
import { decideLabel } from '@/services/apiEndpoints/vision.endpoint';
import { QUALITY_FLAGS, type QualityFlag } from '@/types/vision';
import { ReviewRow } from './components/ReviewRow';
import styles from './ReviewPage.module.css';

export function ReviewPage() {
  const { t } = useI18n();
  const queue = useReviewQueue();
  const queryClient = useQueryClient();
  const seedMutation = useSeedDemoBatch();
  const canLabel = useCan('ai:task:label');
  const canSnapshot = useCan('ai:dataset:snapshot');
  const canEvaluate = useCan('ai:model:evaluate');
  const canOpenDatasets = canSnapshot || canEvaluate;
  const canOpenVision = useCan('ai:metrics:read');
  const [isBatchApproving, setIsBatchApproving] = useState(false);
  const [batchError, setBatchError] = useState<unknown>(null);
  const [filterMode, setFilterMode] = useState<'ALL' | 'EXACT' | 'CORRECTED'>('ALL');
  const [flagFilter, setFlagFilter] = useState<QualityFlag | null>(null);

  const items = queue.data || [];
  const exactMatches = items.filter(
    (item) => item.machine_plate && item.confirmed_plate && item.machine_plate === item.confirmed_plate,
  );
  const correctedItems = items.filter((item) => item.label.verdict === 'CORRECTED');

  const filteredItems = items.filter((item) => {
    if (filterMode === 'EXACT' && !(item.machine_plate && item.confirmed_plate && item.machine_plate === item.confirmed_plate)) {
      return false;
    }
    if (filterMode === 'CORRECTED' && item.label.verdict !== 'CORRECTED') {
      return false;
    }
    if (flagFilter && !(item.label.quality_flags ?? []).includes(flagFilter)) {
      return false;
    }
    return true;
  });

  const handleApproveAllExact = async () => {
    if (exactMatches.length === 0 || isBatchApproving) return;
    setIsBatchApproving(true);
    setBatchError(null);
    try {
      for (const item of exactMatches) {
        // Lý do ghi vào nhật ký kiểm toán phía server (tiếng Việt như mọi lý do khác), không phải chữ hiển thị.
        await decideLabel(item.label.id, 'APPROVED', 'Duyệt nhanh theo lô: Khớp 100%');
      }
    } catch (error) {
      setBatchError(error);
    } finally {
      // Lô đứt giữa chừng thì các nhãn trước đó đã duyệt rồi: luôn làm mới cả nhóm như useVisionMutation.
      void queryClient.invalidateQueries({ queryKey: queryKeys.vision.all() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.audit.list() });
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

      {/* Thanh điều hướng Quy trình 4-Mắt */}
      <div className={styles.workflowBanner}>
        <div>
          <strong>{t.review.workflowTitle} </strong>
          <span className={styles.workflowDesc}>{t.review.workflowDesc}</span>
        </div>
        <div className={styles.workflowLinks}>
          {canLabel && (
            <Link to="/vision/label" className={styles.workflowLinkGhost}>
              {t.review.goToLabel}
            </Link>
          )}
          {canOpenDatasets ? (
            <Link to="/vision/datasets" className={styles.workflowLinkAccent}>
              {t.review.goToDatasets}
            </Link>
          ) : canOpenVision ? (
            <Link to="/vision" className={styles.workflowLinkAccent}>
              {t.nav.visionOverview} →
            </Link>
          ) : null}
        </div>
      </div>

      {queue.isPending && <Loading />}
      {queue.error && <ErrorBlock error={queue.error} onRetry={() => void queue.refetch()} />}
      {batchError != null && <ErrorBlock error={batchError} />}

      {items.length === 0 && !queue.isPending && (
        <div className={styles.emptyWrap}>
          <EmptyState
            icon={<ClipboardCheck size={28} />}
            title={t.review.empty}
            description={t.review.emptyDesc}
          />
          <div className={styles.emptySeedRow}>
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
                <span className={`${styles.statValue} ${styles.statValueSuccess}`}>
                  {t.review.samples(exactMatches.length)}
                </span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statLabel}>{t.review.statCorrected}</span>
                <span className={`${styles.statValue} ${styles.statValueAccent}`}>
                  {t.review.samples(correctedItems.length)}
                </span>
              </div>
            </div>

            <div className={styles.toolbarActions}>
              {/* Filter buttons */}
              <div className={styles.filterPillGroup}>
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

              <div
                role="group"
                aria-label={t.label.flagsTitle}
                className={styles.flagFilterGroup}
              >
                {QUALITY_FLAGS.map((flag) => {
                  const active = flagFilter === flag;
                  return (
                    <Button
                      key={flag}
                      variant={active ? 'secondary' : 'ghost'}
                      size="sm"
                      aria-pressed={active}
                      onClick={() => setFlagFilter(active ? null : flag)}
                    >
                      {t.label.flags[flag]}
                    </Button>
                  );
                })}
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
