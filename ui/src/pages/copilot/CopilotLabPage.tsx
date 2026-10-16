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
import { DASH, fmtDateTime, fmtInt, fmtMs, fmtUsd } from '@/utils/format';
import { ReviewForm } from './ReviewForm';
import { STATUS_LABEL, STATUS_TONE, VERDICT_LABEL, VERDICT_TONE } from './labels';
import styles from './CopilotLabPage.module.css';

type StatusOption = TurnStatus | 'all';
type FeedbackOption = 'all' | 'down' | 'up';

const STATUS_OPTIONS: { value: StatusOption; label: string }[] = [
  { value: 'all', label: 'Tất cả' },
  { value: 'SUCCESS', label: STATUS_LABEL.SUCCESS },
  { value: 'REFUSED', label: STATUS_LABEL.REFUSED },
  { value: 'NO_CONTEXT', label: STATUS_LABEL.NO_CONTEXT },
  { value: 'ERROR', label: STATUS_LABEL.ERROR },
];
const FEEDBACK_OPTIONS: { value: FeedbackOption; label: string }[] = [
  { value: 'all', label: 'Mọi phản hồi' },
  { value: 'down', label: 'Chưa đúng' },
  { value: 'up', label: 'Hữu ích' },
];

function toFilter(status: StatusOption, feedback: FeedbackOption): TurnFilter {
  return {
    status: status === 'all' ? undefined : status,
    feedback: feedback === 'all' ? undefined : feedback === 'up' ? 1 : -1,
  };
}

function FeedbackMark({ value }: { value: Turn['feedback'] }) {
  if (value === 1) return <ThumbsUp size={14} aria-label="Người dùng chấm hữu ích" />;
  if (value === -1) return <ThumbsDown size={14} aria-label="Người dùng chấm chưa đúng" />;
  return null;
}

function TurnDetail({ turn, canReview }: { turn: Turn; canReview: boolean }) {
  const tokens = turn.input_tokens == null ? DASH : `${fmtInt(turn.input_tokens)} / ${fmtInt(turn.output_tokens)}`;
  return (
    <article className={styles.detail} aria-label="Chi tiết lượt">
      <section>
        <h2 className={styles.label}>Câu hỏi (đã che PII)</h2>
        <p className={styles.text}>{turn.query}</p>
      </section>
      <section>
        <h2 className={styles.label}>Câu trả lời</h2>
        <p className={styles.text}>{turn.answer || (turn.error_code ? `Lỗi: ${turn.error_code}` : DASH)}</p>
      </section>
      <dl className={styles.meta}>
        <dt>Lúc</dt><dd className="num">{fmtDateTime(turn.at)}</dd>
        <dt>Trạng thái</dt><dd><Badge tone={STATUS_TONE[turn.status]}>{STATUS_LABEL[turn.status]}</Badge></dd>
        <dt>Prompt</dt><dd className={styles.mono}>{turn.prompt_version || DASH}</dd>
        <dt>Model</dt><dd className={styles.mono}>{turn.model || DASH}</dd>
        <dt>Độ trễ</dt><dd className="num">{fmtMs(turn.latency_ms)}</dd>
        <dt>Token vào / ra</dt><dd className="num">{tokens}</dd>
        <dt>Chi phí</dt><dd className="num">{fmtUsd(turn.cost_usd)}</dd>
        <dt>Vai trò người hỏi</dt><dd>{turn.user_role || DASH}</dd>
        <dt>Bãi</dt><dd className={styles.mono}>{turn.parking_lot_id || DASH}</dd>
        <dt>Mã lượt</dt><dd className={styles.mono}>{turn.turn_id}</dd>
      </dl>
      {turn.review && (
        <p className={styles.reviewed}>
          <Badge tone={VERDICT_TONE[turn.review.verdict]}>{VERDICT_LABEL[turn.review.verdict]}</Badge>
          {turn.review.reviewer} · {fmtDateTime(turn.review.reviewed_at)}
          {turn.review.note && ` — ${turn.review.note}`}
        </p>
      )}
      {canReview ? (
        <ReviewForm key={turn.turn_id} turn={turn} />
      ) : (
        <p className={styles.hint}>Chỉ Reviewer hoặc AI Lead chấm được lượt này.</p>
      )}
    </article>
  );
}

export function CopilotLabPage() {
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
        title="Copilot Lab"
        description="Lượt hỏi gần nhất, câu chữ đã che PII. Chấm đúng/sai để có tỉ lệ đúng thật và gom ca vào bộ eval."
      />
      <div className={styles.filters}>
        <Segmented label="Lọc theo trạng thái" value={status} options={STATUS_OPTIONS} onChange={setStatus} />
        <Segmented label="Lọc theo phản hồi người dùng" value={feedback} options={FEEDBACK_OPTIONS} onChange={setFeedback} />
      </div>
      {turns.isPending && <Loading />}
      {turns.error && <ErrorBlock error={turns.error} onRetry={() => void turns.refetch()} />}
      {turns.isSuccess && rows.length === 0 && (
        <EmptyState icon={<MessagesSquare size={28} />} title="Không có lượt nào khớp bộ lọc" description="Lượt cũ hơn hạn lưu telemetry (mặc định 30 ngày) đã bị xoá." />
      )}
      {rows.length > 0 && (
        <div className={styles.split}>
          <div className={styles.list}>
            <ul className={styles.rows} aria-label="Danh sách lượt">
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
                      <Badge tone={STATUS_TONE[turn.status]}>{STATUS_LABEL[turn.status]}</Badge>
                      {turn.review && <Badge tone={VERDICT_TONE[turn.review.verdict]}>{VERDICT_LABEL[turn.review.verdict]}</Badge>}
                      <FeedbackMark value={turn.feedback} />
                    </span>
                    <span className={styles.query}>{turn.query}</span>
                  </button>
                </li>
              ))}
            </ul>
            {turns.hasNextPage && (
              <Button variant="secondary" onClick={() => void turns.fetchNextPage()} loading={turns.isFetchingNextPage}>
                Tải thêm
              </Button>
            )}
          </div>
          <div className={styles.pane}>
            {selected ? (
              <TurnDetail turn={selected} canReview={canReview} />
            ) : (
              <EmptyState title="Chọn một lượt để xem và chấm" />
            )}
          </div>
        </div>
      )}
    </>
  );
}
