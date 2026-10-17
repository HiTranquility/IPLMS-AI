import { MessagesSquare, ThumbsDown, ThumbsUp } from 'lucide-react';
import { useState } from 'react';
import type { Turn, TurnFilter, TurnStatus } from '@/api/types';
import { Button } from '@/components/common/Ui/button/Button';
import { Segmented } from '@/components/common/Ui/button/Segmented';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { PageHeader } from '@/components/layout/PageHeader';
import { useCan, useTurns } from '@/hooks/useConsole';
import { useI18n } from '@/i18n/I18nProvider';
import type { Messages } from '@/i18n/vi';
import { DASH, fmtDateTime, fmtInt, fmtMs, fmtUsd } from '@/utils/format';
import { ReviewForm } from './ReviewForm';
import { STATUS_TONE, VERDICT_TONE } from './labels';
import styles from './CopilotLabPage.module.css';

type StatusOption = TurnStatus | 'all';
type FeedbackOption = 'all' | 'down' | 'up';

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

function toFilter(status: StatusOption, feedback: FeedbackOption): TurnFilter {
  return {
    status: status === 'all' ? undefined : status,
    feedback: feedback === 'all' ? undefined : feedback === 'up' ? 1 : -1,
  };
}

function FeedbackMark({ value }: { value: Turn['feedback'] }) {
  const { t } = useI18n();
  if (value === 1) return <ThumbsUp size={14} aria-label={t.copilot.markedUp} />;
  if (value === -1) return <ThumbsDown size={14} aria-label={t.copilot.markedDown} />;
  return null;
}

function TurnDetail({ turn, canReview }: { turn: Turn; canReview: boolean }) {
  const { t } = useI18n();
  const tokens = turn.input_tokens == null ? DASH : `${fmtInt(turn.input_tokens)} / ${fmtInt(turn.output_tokens)}`;
  return (
    <article className={styles.detail} aria-label={t.copilot.detail}>
      <section>
        <h2 className={styles.label}>{t.copilot.question}</h2>
        <p className={styles.text}>{turn.query}</p>
      </section>
      <section>
        <h2 className={styles.label}>{t.copilot.answer}</h2>
        <p className={styles.text}>{turn.answer || (turn.error_code ? t.copilot.errorAnswer(turn.error_code) : DASH)}</p>
      </section>
      <dl className={styles.meta}>
        <dt>{t.copilot.at}</dt><dd className="num">{fmtDateTime(turn.at)}</dd>
        <dt>{t.copilot.statusField}</dt><dd><Badge tone={STATUS_TONE[turn.status]}>{t.copilot.status[turn.status]}</Badge></dd>
        <dt>Prompt</dt><dd className={styles.mono}>{turn.prompt_version || DASH}</dd>
        <dt>Model</dt><dd className={styles.mono}>{turn.model || DASH}</dd>
        <dt>{t.copilot.latency}</dt><dd className="num">{fmtMs(turn.latency_ms)}</dd>
        <dt>{t.copilot.tokens}</dt><dd className="num">{tokens}</dd>
        <dt>{t.copilot.cost}</dt><dd className="num">{fmtUsd(turn.cost_usd)}</dd>
        <dt>{t.copilot.role}</dt><dd>{turn.user_role || DASH}</dd>
        <dt>{t.copilot.lot}</dt><dd className={styles.mono}>{turn.parking_lot_id || DASH}</dd>
        <dt>{t.copilot.turnId}</dt><dd className={styles.mono}>{turn.turn_id}</dd>
      </dl>
      {turn.review && (
        <p className={styles.reviewed}>
          <Badge tone={VERDICT_TONE[turn.review.verdict]}>{t.copilot.verdict[turn.review.verdict]}</Badge>
          {turn.review.reviewer} · {fmtDateTime(turn.review.reviewed_at)}
          {turn.review.note && ` — ${turn.review.note}`}
        </p>
      )}
      {canReview ? (
        <ReviewForm key={turn.turn_id} turn={turn} />
      ) : (
        <p className={styles.hint}>{t.copilot.onlyReviewer}</p>
      )}
    </article>
  );
}

export function CopilotLabPage() {
  const { t } = useI18n();
  const [status, setStatus] = useState<StatusOption>('all');
  const [feedback, setFeedback] = useState<FeedbackOption>('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const turns = useTurns(toFilter(status, feedback));
  const canReview = useCan('ai:label:approve');
  const rows = turns.data?.pages.flat() ?? [];
  const selected = rows.find((t) => t.turn_id === selectedId) ?? null;

  return (
    <>
      <PageHeader
        title={t.copilot.title}
        description={t.copilot.desc}
      />
      <div className={styles.filters}>
        <Segmented label={t.copilot.filterStatus} value={status} options={statusOptions(t)} onChange={setStatus} />
        <Segmented label={t.copilot.filterFeedback} value={feedback} options={feedbackOptions(t)} onChange={setFeedback} />
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
  );
}
