import { CheckCircle2, MessagesSquare, Search, TrendingUp } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Button } from '@/components/common/Ui/button/Button';
import { Segmented } from '@/components/common/Ui/button/Segmented';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { PageHeader } from '@/components/layout/PageHeader';
import { useI18n } from '@/i18n/I18nProvider';
import type { Messages } from '@/i18n/vi';
import { fmtDateTime } from '@/utils/format';
import { FeedbackMark } from './components/FeedbackMark';
import { TurnDetail } from './components/TurnDetail';
import { ChatStudio } from './components/ChatStudio';
import {
  CopilotLabPageProvider,
  useCopilotLabPageContext,
  type FeedbackOption,
  type StatusOption,
  type TimeRangeOption,
} from './CopilotLabPageContext';
import { STATUS_TONE, VERDICT_TONE } from './labels';
import styles from './CopilotLabPage.module.css';

const statusOptions = (t: Messages): { value: StatusOption; label: string }[] => [
  { value: 'all', label: t.copilot.all },
  { value: 'SUCCESS', label: t.copilot.status.SUCCESS },
  { value: 'REFUSED', label: t.copilot.status.REFUSED },
  { value: 'NO_CONTEXT', label: t.copilot.status.NO_CONTEXT },
  { value: 'ERROR', label: t.copilot.status.ERROR },
];

const feedbackOptions = (t: Messages): { value: FeedbackOption; label: string }[] => [
  { value: 'all', label: t.copilot.allFeedback },
  { value: 'down', label: t.copilot.feedbackDown },
  { value: 'up', label: t.copilot.feedbackUp },
];

const timeOptions = (t: Messages): { value: TimeRangeOption; label: string }[] => [
  { value: 'all', label: t.copilot.timeAll },
  { value: 'today', label: t.copilot.timeToday },
  { value: '3days', label: t.copilot.time3Days },
  { value: '7days', label: t.copilot.time7Days },
];

export interface CopilotLabPageProps {
  initialMode?: 'chat' | 'review';
}

function CopilotLabPageContent({ initialMode = 'review' }: CopilotLabPageProps) {
  const { t } = useI18n();
  const location = useLocation();
  const navigate = useNavigate();

  const isLogs = location.pathname.endsWith('/logs');
  const isChatRoute = location.pathname.endsWith('/copilot');
  const viewMode: 'chat' | 'review' = isLogs ? 'review' : (isChatRoute ? 'chat' : initialMode);

  const handleModeChange = (val: string) => {
    if (val === 'chat') {
      navigate('/copilot');
    } else {
      navigate('/copilot/logs');
    }
  };
  const {
    status,
    setStatus,
    feedback,
    setFeedback,
    timeRange,
    setTimeRange,
    searchQuery,
    setSearchQuery,
    selectedId,
    setSelectedId,
    turns,
    rows,
    selected,
    canReview,
    stats,
  } = useCopilotLabPageContext();

  return (
    <>
      <PageHeader
        title={t.copilot.title}
        description={t.copilot.desc}
        actions={
          <Segmented
            label={t.copilot.title}
            value={viewMode}
            options={[
              { value: 'chat', label: t.copilot.modeChat },
              { value: 'review', label: t.copilot.modeReview },
            ]}
            onChange={handleModeChange}
          />
        }
      />

      {viewMode === 'chat' ? (
        <ChatStudio />
      ) : (
        <>
          {/* 1. Dải tiến độ thẩm định & độ chính xác thực tế (Review Progress Strip) */}
          {turns.isSuccess && stats.total > 0 && (
            <div className={styles.progressStrip} role="region" aria-label={t.copilot.progressTitle}>
              <div className={styles.progressMain}>
                <div className={styles.progressTitleGroup}>
                  <CheckCircle2 size={16} className={styles.progressIcon} />
                  <span className={styles.progressTitleText}>{t.copilot.progressTitle}</span>
                  <span className={styles.progressCountBadge}>
                    {stats.reviewed} / {stats.total} ({stats.progressPct}%)
                  </span>
                </div>
                <div className={styles.progressBarTrack}>
                  <div
                    className={styles.progressBarFill}
                    style={{ width: `${stats.progressPct}%` }}
                  />
                </div>
              </div>

              <div className={styles.progressKpiGrid}>
                <div className={styles.progressKpiItem}>
                  <span className={styles.progressKpiLabel}>{t.copilot.progressAccuracy}</span>
                  <div className={styles.progressKpiValue}>
                    <TrendingUp size={13} className={styles.accuracyIcon} />
                    <span className="num">{stats.accuracyPct}%</span>
                  </div>
                </div>

                <div className={styles.progressKpiItem}>
                  <span className={styles.progressKpiLabel}>{t.copilot.progressRemaining}</span>
                  <div className={styles.progressKpiValue}>
                    <span className="num">{stats.pending}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 2. Thanh lọc, tìm kiếm và phân đoạn thời gian */}
          <div className={styles.filtersBar}>
            <div className={styles.searchBox}>
              <Search size={14} className={styles.searchIcon} />
              <input
                type="text"
                className={styles.searchInput}
                placeholder={t.copilot.searchPlaceholder}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label={t.copilot.searchLabel}
              />
              {searchQuery && (
                <button
                  type="button"
                  className={styles.searchClearBtn}
                  onClick={() => setSearchQuery('')}
                  aria-label={t.copilot.clearSearch}
                  title={t.copilot.clearSearch}
                >
                  ✕
                </button>
              )}
            </div>

            <div className={styles.filters}>
              <Segmented label={t.copilot.timeRange} value={timeRange} options={timeOptions(t)} onChange={setTimeRange} />
              <Segmented label={t.copilot.filterStatus} value={status} options={statusOptions(t)} onChange={setStatus} />
              <Segmented label={t.copilot.filterFeedback} value={feedback} options={feedbackOptions(t)} onChange={setFeedback} />
            </div>
          </div>

          {turns.isPending && <Loading />}
          {turns.error && <ErrorBlock error={turns.error} onRetry={() => void turns.refetch()} />}
          {turns.isSuccess && rows.length === 0 && (
            <EmptyState icon={<MessagesSquare size={28} />} title={t.copilot.emptyTitle} description={t.copilot.emptyDesc} />
          )}

          {rows.length > 0 && (
            <div className={styles.split}>
              <div className={styles.list}>
                <ul className={styles.rows} aria-label={t.copilot.listLabel}>
                  {rows.map((turn) => (
                    <li key={turn.turn_id}>
                      <button
                        type="button"
                        className={styles.row}
                        aria-current={turn.turn_id === selectedId || undefined}
                        onClick={() => setSelectedId(turn.turn_id)}
                      >
                        <span className={styles.rowTop}>
                          <span className="num">{fmtDateTime(turn.at)}</span>
                          <Badge tone={STATUS_TONE[turn.status]}>{t.copilot.status[turn.status]}</Badge>
                          {turn.review && <Badge tone={VERDICT_TONE[turn.review.verdict]}>{t.copilot.verdict[turn.review.verdict]}</Badge>}
                          <FeedbackMark value={turn.feedback} />
                        </span>
                        <span className={styles.query}>{turn.query}</span>
                      </button>
                    </li>
                  ))}
                </ul>
                {turns.hasNextPage && (
                  <Button variant="secondary" onClick={() => void turns.fetchNextPage()} loading={turns.isFetchingNextPage}>
                    {t.copilot.loadMore}
                  </Button>
                )}
              </div>
              <div className={styles.pane}>
                {selected ? (
                  <TurnDetail turn={selected} canReview={canReview} />
                ) : (
                  <EmptyState title={t.copilot.pick} />
                )}
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}

export function CopilotLabPage({ initialMode = 'review' }: CopilotLabPageProps) {
  return (
    <CopilotLabPageProvider>
      <CopilotLabPageContent initialMode={initialMode} />
    </CopilotLabPageProvider>
  );
}

export default CopilotLabPage;
