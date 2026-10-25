import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { PageHeader } from '@/components/layout/PageHeader';
import { useLabelQueue } from '@/hooks/queries/useVisionQueries';
import { useI18n } from '@/i18n/I18nProvider';
import type { LabelVerdict } from '@/types/vision';
import { fmtPercent } from '@/utils/format';
import {
  LabelEmptyStudio,
  LabelHistoryDrawer,
  LabelMetricsStrip,
  LabelShortcutsBar,
  LabelWorkspace,
  type HistoryItem,
} from './components/LabelStudio';
import styles from './LabelPage.module.css';
import studioStyles from './components/LabelStudio/LabelStudio.module.css';

type QueueFilter = 'all' | 'staff' | 'low_conf';

export function LabelPage() {
  const { t } = useI18n();
  const w = t.label.workspace;
  const queue = useLabelQueue();

  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [filter, setFilter] = useState<QueueFilter>('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [skippedIds, setSkippedIds] = useState<string[]>([]);

  // Tính toán thời gian gán trung bình s/mẫu
  const [sessionStartTime] = useState<number>(Date.now());
  const elapsedSeconds = Math.max(1, Math.round((Date.now() - sessionStartTime) / 1000));
  const avgVelocity = history.length > 0 ? Math.round(elapsedSeconds / history.length) : 0;

  const allSamples = queue.data ?? [];
  const staffCount = useMemo(() => allSamples.filter((s) => s.human_corrected).length, [allSamples]);
  const lowConfCount = useMemo(
    () => allSamples.filter((s) => (s.machine_confidence ?? 1) < 0.85 || s.selection_reasons.includes('low_confidence')).length,
    [allSamples],
  );

  const filteredQueue = useMemo(() => {
    const base = allSamples.filter((s) => {
      if (filter === 'staff') return s.human_corrected;
      if (filter === 'low_conf') {
        return (s.machine_confidence ?? 1) < 0.85 || s.selection_reasons.includes('low_confidence');
      }
      return true;
    });
    // Đưa các mẫu đã bấm "Bỏ qua tạm" xuống cuối danh sách để ưu tiên mẫu chưa xem
    const unskipped = base.filter((s) => !skippedIds.includes(s.capture_id));
    const skipped = base.filter((s) => skippedIds.includes(s.capture_id));
    return [...unskipped, ...skipped];
  }, [allSamples, filter, skippedIds]);

  const current = useMemo(() => {
    if (selectedId) {
      const found = filteredQueue.find((s) => s.capture_id === selectedId);
      if (found) return found;
    }
    return filteredQueue[0];
  }, [filteredQueue, selectedId]);

  const handleLabeled = (captureId: string, verdict: LabelVerdict, plateText: string) => {
    setHistory((prev) => [
      {
        captureId,
        verdict,
        plateText,
        timestamp: new Date(),
      },
      ...prev,
    ]);
    setSkippedIds((prev) => prev.filter((id) => id !== captureId));
    setSelectedId(null);
    void queue.refetch();
  };

  const handleSkip = (captureId: string) => {
    setSkippedIds((prev) => [...prev.filter((id) => id !== captureId), captureId]);
    const idx = filteredQueue.findIndex((s) => s.capture_id === captureId);
    const next = filteredQueue[idx + 1] ?? filteredQueue[0];
    if (next && next.capture_id !== captureId) {
      setSelectedId(next.capture_id);
    } else {
      setSelectedId(null);
    }
  };

  return (
    <div className={styles.page}>
      <PageHeader
        title={t.label.title}
        description={t.label.desc}
      />

      {/* Chu trình Chuẩn hóa Dữ liệu ANPR 4-Mắt */}
      <div className={studioStyles.workflowBanner}>
        <div className={studioStyles.workflowSteps}>
          <strong>{t.label.studio.workflowTitle}</strong>
          <span className={studioStyles.workflowStepActive}>{t.label.studio.workflowStep1}</span>
          <span className={studioStyles.workflowArrow}>→</span>
          <span className={studioStyles.workflowStepMuted}>{t.label.studio.workflowStep2}</span>
          <span className={studioStyles.workflowArrow}>→</span>
          <span className={studioStyles.workflowStepMuted}>{t.label.studio.workflowStep3}</span>
        </div>
        <Link to="/vision/review" className={studioStyles.workflowLink}>
          {t.label.studio.goToReview}
        </Link>
      </div>

      {/* Thanh đo lường hiệu suất & thao tác nhanh */}
      <LabelMetricsStrip
        queueCount={allSamples.length}
        sessionCount={history.length}
        avgVelocitySeconds={avgVelocity}
        onRefresh={() => void queue.refetch()}
        isRefreshing={queue.isFetching}
        onToggleHistory={() => setShowHistory((h) => !h)}
        showHistory={showHistory}
      />

      {/* Bộ lọc hàng đợi & Filmstrip điều hướng mẫu chuyên sâu */}
      {allSamples.length > 0 && (
        <div className={studioStyles.filmstripCard}>
          <div className={studioStyles.filmstripHeader}>
            <span className={studioStyles.filmstripTitle}>{w.filmstripTitle}</span>
            <div className={studioStyles.filterGroup}>
              <button
                type="button"
                className={`${studioStyles.filterChip} ${filter === 'all' ? studioStyles.filterChipActive : ''}`}
                onClick={() => {
                  setFilter('all');
                  setSelectedId(null);
                }}
              >
                {w.filterAll(allSamples.length)}
              </button>
              <button
                type="button"
                className={`${studioStyles.filterChip} ${filter === 'staff' ? studioStyles.filterChipActive : ''}`}
                onClick={() => {
                  setFilter('staff');
                  setSelectedId(null);
                }}
              >
                {w.filterStaffFixed(staffCount)}
              </button>
              <button
                type="button"
                className={`${studioStyles.filterChip} ${filter === 'low_conf' ? studioStyles.filterChipActive : ''}`}
                onClick={() => {
                  setFilter('low_conf');
                  setSelectedId(null);
                }}
              >
                {w.filterLowConf(lowConfCount)}
              </button>
            </div>
          </div>

          <div className={studioStyles.filmstripList} role="list">
            {filteredQueue.map((item, idx) => {
              const isActive = current?.capture_id === item.capture_id;
              const isSkipped = skippedIds.includes(item.capture_id);
              return (
                <button
                  key={item.capture_id}
                  type="button"
                  role="listitem"
                  className={`${studioStyles.filmstripItem} ${isActive ? studioStyles.filmstripItemActive : ''}`}
                  onClick={() => setSelectedId(item.capture_id)}
                >
                  <div className={studioStyles.filmstripTop}>
                    <span className={studioStyles.filmstripIndex}>#{idx + 1}</span>
                    <span className={studioStyles.filmstripConf}>
                      {fmtPercent(item.machine_confidence)}
                    </span>
                  </div>
                  <div className={studioStyles.filmstripPlate}>
                    {item.machine_plate || item.confirmed_plate || '—'}
                  </div>
                  {isSkipped && <span className={studioStyles.filmstripSkipped}>{w.SkippedBadge}</span>}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Trạng thái tải & lỗi */}
      {queue.isPending && <Loading />}
      {queue.error && <ErrorBlock error={queue.error} onRetry={() => void queue.refetch()} />}

      {/* Khi hàng đợi trống: Render Empty Studio Hub đầy đủ tính năng nạp & SOP */}
      {queue.isSuccess && !current && (
        <LabelEmptyStudio onSeeded={() => void queue.refetch()} />
      )}

      {/* Khi có mẫu đang chờ gán nhãn: Render Workspace 2 cột chuẩn Enterprise */}
      {current && (
        <>
          <LabelWorkspace
            key={current.capture_id}
            sample={current}
            remaining={filteredQueue.length}
            onLabeled={handleLabeled}
            onSkip={() => handleSkip(current.capture_id)}
          />
          <LabelShortcutsBar />
        </>
      )}

      {/* Lịch sử phiên làm việc */}
      {showHistory && <LabelHistoryDrawer items={history} />}
    </div>
  );
}

export default LabelPage;
