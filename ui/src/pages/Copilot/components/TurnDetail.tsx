import { Badge } from '@/components/common/Ui/data-display/Badge';
import { useI18n } from '@/i18n/I18nProvider';
import type { Turn } from '@/types/copilot';
import { DASH, fmtDateTime, fmtInt, fmtMs, fmtUsd } from '@/utils/format';
import { STATUS_TONE, VERDICT_TONE } from '../labels';
import { ReviewForm } from './ReviewForm';
import styles from '../CopilotLabPage.module.css';

export interface TurnDetailProps {
  turn: Turn;
  canReview: boolean;
}

export function TurnDetail({ turn, canReview }: TurnDetailProps) {
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
        <dt>Tốc độ</dt><dd className="num">{turn.speed_tok_s ? `${turn.speed_tok_s} tok/s` : DASH}</dd>
        <dt>Ngữ cảnh</dt><dd className="num">{turn.input_tokens ? `${fmtInt(turn.input_tokens)} / 4,096` : DASH}</dd>
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

export default TurnDetail;
