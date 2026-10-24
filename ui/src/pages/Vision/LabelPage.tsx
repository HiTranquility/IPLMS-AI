import { useState } from 'react';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { PageHeader } from '@/components/layout/PageHeader';
import { useLabelQueue } from '@/hooks/queries/useVisionQueries';
import { useI18n } from '@/i18n/I18nProvider';
import type { LabelVerdict } from '@/types/vision';
import {
  LabelEmptyStudio,
  LabelHistoryDrawer,
  LabelMetricsStrip,
  LabelShortcutsBar,
  LabelWorkspace,
  type HistoryItem,
} from './components/LabelStudio';
import styles from './LabelPage.module.css';

export function LabelPage() {
  const { t } = useI18n();
  const queue = useLabelQueue();
  const current = queue.data?.[0];

  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  // Tính toán thời gian gán trung bình s/mẫu
  const [sessionStartTime] = useState<number>(Date.now());
  const elapsedSeconds = Math.max(1, Math.round((Date.now() - sessionStartTime) / 1000));
  const avgVelocity = history.length > 0 ? Math.round(elapsedSeconds / history.length) : 0;

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
    void queue.refetch();
  };

  return (
    <div className={styles.page}>
      <PageHeader
        title={t.label.title}
        description={t.label.desc}
      />

      {/* Thanh đo lường hiệu suất & thao tác nhanh */}
      <LabelMetricsStrip
        queueCount={queue.data?.length ?? 0}
        sessionCount={history.length}
        avgVelocitySeconds={avgVelocity}
        onRefresh={() => void queue.refetch()}
        isRefreshing={queue.isFetching}
        onToggleHistory={() => setShowHistory((h) => !h)}
        showHistory={showHistory}
      />

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
            remaining={queue.data!.length}
            onLabeled={handleLabeled}
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
