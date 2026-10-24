import { CheckCircle, Coins, PieChart, ShieldCheck, ThumbsUp } from 'lucide-react';
import { useI18n } from '@/i18n/I18nProvider';
import type { ReviewStats, UsageSummary } from '@/types/copilot';
import { DASH, fmtInt, fmtPercent, fmtUsd, ratio } from '@/utils/format';
import styles from './DistributionSection.module.css';

export interface DistributionSectionProps {
  usage: UsageSummary;
  review: ReviewStats;
}

export function DistributionSection({ usage, review }: DistributionSectionProps) {
  const { t } = useI18n();

  const total = usage.total_requests || 1;
  const pSuccess = (usage.success_requests / total) * 100;
  const pRefused = (usage.refused_requests / total) * 100;
  const pNoContext = (usage.no_context_requests / total) * 100;
  const pError = (usage.error_requests / total) * 100;

  const totalTokens = usage.input_tokens + usage.output_tokens || 1;
  const pInputToken = (usage.input_tokens / totalTokens) * 100;
  const pOutputToken = (usage.output_tokens / totalTokens) * 100;

  const rated = usage.thumbs_up + usage.thumbs_down;
  const pHelpful = rated > 0 ? ratio(usage.thumbs_up, rated) : null;

  return (
    <div className={styles.grid}>
      {/* Cột 1: Phân bổ Trạng thái Câu hỏi */}
      <div className={styles.card}>
        <div className={styles.cardHeader}>
          <PieChart size={16} className={styles.cardIcon} aria-hidden />
          <h4 className={styles.cardTitle}>{t.overview.distributionTitle}</h4>
        </div>

        <div className={styles.barTrack} aria-hidden>
          <div className={styles.barSegment} style={{ width: `${pSuccess}%`, background: 'var(--color-success)' }} />
          <div className={styles.barSegment} style={{ width: `${pRefused}%`, background: 'var(--color-warning)' }} />
          <div className={styles.barSegment} style={{ width: `${pNoContext}%`, background: 'var(--color-info)' }} />
          <div className={styles.barSegment} style={{ width: `${pError}%`, background: 'var(--color-danger)' }} />
        </div>

        <div className={styles.list}>
          <div className={styles.row}>
            <span className={styles.rowLabel}>
              <span className={styles.rowDot} style={{ background: 'var(--color-success)' }} />
              {t.overview.answered}
            </span>
            <span className={styles.rowValue}>
              {fmtInt(usage.success_requests)}
              <span className={styles.rowSub}>({pSuccess.toFixed(1)}%)</span>
            </span>
          </div>

          <div className={styles.row}>
            <span className={styles.rowLabel}>
              <span className={styles.rowDot} style={{ background: 'var(--color-warning)' }} />
              {t.overview.refused}
            </span>
            <span className={styles.rowValue}>
              {fmtInt(usage.refused_requests)}
              <span className={styles.rowSub}>({pRefused.toFixed(1)}%)</span>
            </span>
          </div>

          <div className={styles.row}>
            <span className={styles.rowLabel}>
              <span className={styles.rowDot} style={{ background: 'var(--color-info)' }} />
              {t.overview.noContext}
            </span>
            <span className={styles.rowValue}>
              {fmtInt(usage.no_context_requests)}
              <span className={styles.rowSub}>({pNoContext.toFixed(1)}%)</span>
            </span>
          </div>

          <div className={styles.row}>
            <span className={styles.rowLabel}>
              <span className={styles.rowDot} style={{ background: 'var(--color-danger)' }} />
              {t.overview.errors}
            </span>
            <span className={styles.rowValue}>
              {fmtInt(usage.error_requests)}
              <span className={styles.rowSub}>({pError.toFixed(1)}%)</span>
            </span>
          </div>
        </div>
      </div>

      {/* Cột 2: Đánh giá & Thẩm định Chất lượng */}
      <div className={styles.card}>
        <div className={styles.cardHeader}>
          <ShieldCheck size={16} className={styles.cardIcon} aria-hidden />
          <h4 className={styles.cardTitle}>{t.overview.ratingsTitle}</h4>
        </div>

        <div className={styles.list}>
          <div className={styles.row}>
            <span className={styles.rowLabel}>
              <CheckCircle size={13} style={{ color: 'var(--color-success)' }} />
              {t.overview.accuracy}
            </span>
            <span className={styles.rowValue}>
              {review.accuracy !== null ? fmtPercent(review.accuracy) : DASH}
              {review.reviewed > 0 && <span className={styles.rowSub}>{t.overview.reviewedCount(review.reviewed)}</span>}
            </span>
          </div>

          <div className={styles.row}>
            <span className={styles.rowLabel}>{t.overview.correct} / {t.overview.incorrect}</span>
            <span className={styles.rowValue}>
              <span style={{ color: 'var(--color-success)' }}>{review.correct}</span>
              {' / '}
              <span style={{ color: 'var(--color-danger)' }}>{review.incorrect}</span>
              {review.unsafe > 0 && (
                <span style={{ color: 'var(--color-warning)', marginLeft: 4 }}>
                  {t.overview.unsafeCount(review.unsafe)}
                </span>
              )}
            </span>
          </div>

          <div className={styles.divider} />

          <div className={styles.row}>
            <span className={styles.rowLabel}>
              <ThumbsUp size={13} style={{ color: 'var(--color-accent)' }} />
              {t.overview.helpful}
            </span>
            <span className={styles.rowValue}>
              {pHelpful !== null ? fmtPercent(pHelpful) : t.overview.noRatings}
            </span>
          </div>

          <div className={styles.row}>
            <span className={styles.rowLabel}>{t.overview.likesDislikes}</span>
            <span className={styles.rowValue}>
              {fmtInt(usage.thumbs_up)} 👍 · {fmtInt(usage.thumbs_down)} 👎
            </span>
          </div>
        </div>
      </div>

      {/* Cột 3: Tiêu thụ Token & Chi phí */}
      <div className={styles.card}>
        <div className={styles.cardHeader}>
          <Coins size={16} className={styles.cardIcon} aria-hidden />
          <h4 className={styles.cardTitle}>{t.overview.tokenCostTitle}</h4>
        </div>

        <div className={styles.barTrack} aria-hidden>
          <div className={styles.barSegment} style={{ width: `${pInputToken}%`, background: 'var(--color-accent)' }} />
          <div className={styles.barSegment} style={{ width: `${pOutputToken}%`, background: 'var(--color-info)' }} />
        </div>

        <div className={styles.list}>
          <div className={styles.row}>
            <span className={styles.rowLabel}>
              <span className={styles.rowDot} style={{ background: 'var(--color-accent)' }} />
              {t.overview.tokenInput}
            </span>
            <span className={styles.rowValue}>
              {fmtInt(usage.input_tokens)}
              <span className={styles.rowSub}>({pInputToken.toFixed(0)}%)</span>
            </span>
          </div>

          <div className={styles.row}>
            <span className={styles.rowLabel}>
              <span className={styles.rowDot} style={{ background: 'var(--color-info)' }} />
              {t.overview.tokenOutput}
            </span>
            <span className={styles.rowValue}>
              {fmtInt(usage.output_tokens)}
              <span className={styles.rowSub}>({pOutputToken.toFixed(0)}%)</span>
            </span>
          </div>

          <div className={styles.divider} />

          <div className={styles.row}>
            <span className={styles.rowLabel}>{t.overview.cost}</span>
            <span className={styles.rowValue} style={{ color: 'var(--color-accent-dark)', fontSize: '13px' }}>
              {usage.cost_known ? fmtUsd(usage.total_cost_usd) : DASH}
            </span>
          </div>

          <div className={styles.row}>
            <span className={styles.rowLabel}>{t.overview.avgCostPerTurn}</span>
            <span className={styles.rowValue}>
              {usage.cost_known ? fmtUsd(usage.avg_cost_usd) : DASH}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DistributionSection;
