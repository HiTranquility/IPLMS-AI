import { useMemo } from 'react';
import { BookOpen, Clock, Coins, Cpu, Gauge } from 'lucide-react';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { Button } from '@/components/common/Ui/button/Button';
import { FormattedAnswer } from '@/components/common/Ui/data-display/FormattedAnswer';
import { usePromoteTurnToEval } from '@/hooks/mutations/useToolMutations';
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
  const promoteEval = usePromoteTurnToEval();
  const tokens = turn.input_tokens == null ? DASH : `${fmtInt(turn.input_tokens)} / ${fmtInt(turn.output_tokens)}`;

  const extractedSources = useMemo(() => {
    const list: string[] = [];
    const customTurn = turn as Turn & { sources?: string[] };
    if (customTurn.sources && Array.isArray(customTurn.sources)) {
      list.push(...customTurn.sources);
    }
    if (turn.answer) {
      const docMatches = turn.answer.match(/\[(DOC-[^\]]+|[A-Za-z0-9_-]+\.(?:md|txt|pdf))\]/gi);
      if (docMatches) {
        docMatches.forEach((m) => {
          const clean = m.replace(/[[\]]/g, '');
          if (!list.includes(clean)) list.push(clean);
        });
      }
    }
    return list;
  }, [turn]);

  return (
    <article className={styles.detail} aria-label={t.copilot.detail}>
      {/* Top Status & Timestamp Header */}
      <div className={styles.detailHeader}>
        <div className={styles.detailHeaderLeft}>
          <Badge tone={STATUS_TONE[turn.status]}>{t.copilot.status[turn.status]}</Badge>
          <span className={styles.detailTimestamp}>{fmtDateTime(turn.at)}</span>
        </div>
        <span className={styles.turnIdPill}>{turn.turn_id.slice(0, 12)}</span>
      </div>

      {/* 4-Chip Telemetry Ribbon */}
      <div className={styles.telemetryRibbon}>
        <div className={styles.telemetryChip}>
          <span className={styles.telemetryChipLabel}>
            <Clock size={12} aria-hidden="true" />
            <span>{t.copilot.latency}</span>
          </span>
          <strong className={styles.telemetryChipValue}>{fmtMs(turn.latency_ms)}</strong>
        </div>
        <div className={styles.telemetryChip}>
          <span className={styles.telemetryChipLabel}>
            <Cpu size={12} aria-hidden="true" />
            <span>{t.copilot.tokens}</span>
          </span>
          <strong className={styles.telemetryChipValue}>{tokens}</strong>
        </div>
        <div className={styles.telemetryChip}>
          <span className={styles.telemetryChipLabel}>
            <Gauge size={12} aria-hidden="true" />
            <span>{t.copilot.speed}</span>
          </span>
          <strong className={styles.telemetryChipValue}>
            {turn.speed_tok_s ? `${turn.speed_tok_s} tok/s` : DASH}
          </strong>
        </div>
        <div className={styles.telemetryChip}>
          <span className={styles.telemetryChipLabel}>
            <Coins size={12} aria-hidden="true" />
            <span>{t.copilot.cost}</span>
          </span>
          <strong className={styles.telemetryChipValue}>{fmtUsd(turn.cost_usd)}</strong>
        </div>
      </div>

      <section className={styles.qaBox}>
        <h2 className={styles.label}>{t.copilot.question}</h2>
        <p className={styles.text}>{turn.query}</p>
      </section>

      <section className={styles.answerBox}>
        <h2 className={styles.label}>{t.copilot.answer}</h2>
        {turn.answer ? (
          <FormattedAnswer content={turn.answer} />
        ) : (
          <p className={styles.text}>{turn.error_code ? t.copilot.errorAnswer(turn.error_code) : DASH}</p>
        )}
      </section>

      <section>
        <h2 className={styles.label}>{t.copilot.sourcesCited}</h2>
        {extractedSources.length > 0 ? (
          <div className={styles.sourcesList}>
            {extractedSources.map((source, idx) => (
              <span key={idx} className={styles.sourceTag}>
                <BookOpen size={12} />
                <span>{source}</span>
              </span>
            ))}
          </div>
        ) : (
          <p className={styles.textMuted}>{t.copilot.noSourcesCited}</p>
        )}
      </section>

      <dl className={styles.meta}>
        <dt>{t.copilot.at}</dt><dd className="num">{fmtDateTime(turn.at)}</dd>
        <dt>{t.copilot.statusField}</dt><dd><Badge tone={STATUS_TONE[turn.status]}>{t.copilot.status[turn.status]}</Badge></dd>
        <dt>Prompt</dt><dd className={styles.mono}>{turn.prompt_version || DASH}</dd>
        <dt>Model</dt><dd className={styles.mono}>{turn.model || DASH}</dd>
        <dt>{t.copilot.context}</dt><dd className="num">{turn.input_tokens ? fmtInt(turn.input_tokens) : DASH}</dd>
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
        <>
          <ReviewForm key={turn.turn_id} turn={turn} />
          <div className={styles.evalPromotionBar}>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              loading={promoteEval.isPending}
              disabled={promoteEval.isSuccess}
              onClick={() =>
                promoteEval.mutate({
                  turnId: turn.turn_id,
                  query: turn.query,
                  expected_behavior: turn.review?.verdict === 'UNSAFE' ? 'REFUSE' : 'ANSWER',
                  category: 'regression',
                  note: turn.review?.note || '',
                })
              }
              title={t.copilot.promoteEvalHint}
            >
              {promoteEval.isSuccess ? t.copilot.promoteEvalDone : t.copilot.promoteEvalBtn}
            </Button>
            <span className={styles.hint}>{t.copilot.promoteEvalHint}</span>
          </div>
        </>
      ) : (
        <p className={styles.hint}>{t.copilot.onlyReviewer}</p>
      )}
    </article>
  );
}

export default TurnDetail;
