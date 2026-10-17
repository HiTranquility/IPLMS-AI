import { useState } from 'react';
import type { ReviewStats, UsageSummary } from '@/api/types';
import { Segmented } from '@/components/common/Ui/button/Segmented';
import { Stat } from '@/components/common/Ui/data-display/Stat';
import table from '@/components/common/Ui/data-display/table.module.css';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { PageHeader } from '@/components/layout/PageHeader';
import { useReviewStats, useUsage } from '@/hooks/useConsole';
import { useI18n } from '@/i18n/I18nProvider';
import { DASH, fmtDay, fmtInt, fmtMs, fmtPercent, fmtUsd, ratio } from '@/utils/format';
import styles from './OverviewPage.module.css';

const WINDOWS = [7, 30, 90];

function UsageSection({ usage }: { usage: UsageSummary }) {
  const { t } = useI18n();
  if (usage.total_requests === 0) {
    return (
      <EmptyState
        title={t.overview.emptyTitle}
        description={t.overview.emptyDesc}
      />
    );
  }
  const rated = usage.thumbs_up + usage.thumbs_down;
  return (
    <>
      <dl className={styles.stats}>
        <Stat label={t.overview.requests} value={fmtInt(usage.total_requests)} />
        <Stat label={t.overview.answered} value={fmtPercent(ratio(usage.success_requests, usage.total_requests))} hint={t.overview.turnCount(fmtInt(usage.success_requests))} />
        <Stat label={t.overview.refused} value={fmtInt(usage.refused_requests)} />
        <Stat label={t.overview.noContext} value={fmtInt(usage.no_context_requests)} />
        <Stat label={t.overview.errors} value={fmtInt(usage.error_requests)} />
      </dl>
      <dl className={styles.stats}>
        <Stat label={t.overview.avgLatency} value={fmtMs(usage.avg_latency_ms)} />
        <Stat label={t.overview.p95Latency} value={fmtMs(usage.p95_latency_ms)} />
        <Stat label={t.overview.tokens} value={`${fmtInt(usage.input_tokens)} / ${fmtInt(usage.output_tokens)}`} />
        <Stat
          label={t.overview.cost}
          value={usage.cost_known ? fmtUsd(usage.total_cost_usd) : DASH}
          hint={usage.cost_known ? t.overview.perTurn(fmtUsd(usage.avg_cost_usd)) : t.overview.costUnknown}
        />
        <Stat
          label={t.overview.helpful}
          value={fmtPercent(ratio(usage.thumbs_up, rated))}
          hint={rated ? t.overview.helpfulHint(fmtInt(usage.thumbs_up), fmtInt(usage.thumbs_down)) : t.overview.noRatings}
        />
      </dl>
      <h2 className={styles.sectionTitle}>{t.overview.byDay}</h2>
      <div className={table.wrap}>
        <table className={table.table}>
          <thead>
            <tr>
              <th scope="col">{t.overview.day}</th>
              <th scope="col" className={table.num}>{t.overview.turns}</th>
              <th scope="col" className={table.num}>{t.overview.refusedShort}</th>
              <th scope="col" className={table.num}>{t.overview.errors}</th>
              <th scope="col" className={table.num}>{t.overview.avgLatency}</th>
            </tr>
          </thead>
          <tbody>
            {usage.days.map((day) => (
              <tr key={day.date}>
                <td>{fmtDay(day.date)}</td>
                <td className={table.num}>{fmtInt(day.requests)}</td>
                <td className={table.num}>{fmtInt(day.refused)}</td>
                <td className={table.num}>{fmtInt(day.errors)}</td>
                <td className={table.num}>{fmtMs(day.avg_latency_ms)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function AccuracySection({ stats }: { stats: ReviewStats }) {
  const { t } = useI18n();
  return (
    <dl className={styles.stats}>
      <Stat
        label={t.overview.accuracy}
        value={fmtPercent(stats.accuracy)}
        hint={stats.reviewed ? t.overview.reviewedHint(fmtInt(stats.reviewed)) : t.overview.noReviews}
      />
      <Stat label={t.overview.correct} value={fmtInt(stats.correct)} />
      <Stat label={t.overview.incorrect} value={fmtInt(stats.incorrect)} />
      <Stat label={t.overview.unsafe} value={fmtInt(stats.unsafe)} />
    </dl>
  );
}

export function OverviewPage() {
  const { t } = useI18n();
  const [days, setDays] = useState(7);
  const usage = useUsage(days);
  const review = useReviewStats(days);

  return (
    <>
      <PageHeader
        title={t.overview.title}
        description={t.overview.desc}
        actions={
          <Segmented label={t.overview.windowLabel} value={days} options={WINDOWS.map((value) => ({ value, label: t.overview.window(value) }))} onChange={setDays} />
        }
      />
      <section aria-labelledby="accuracy-title" className={styles.section}>
        <h2 id="accuracy-title" className={styles.sectionTitle}>{t.overview.quality}</h2>
        {review.isPending && <Loading />}
        {review.error && <ErrorBlock error={review.error} onRetry={() => void review.refetch()} />}
        {review.data && <AccuracySection stats={review.data} />}
      </section>
      <section aria-labelledby="usage-title" className={styles.section}>
        <h2 id="usage-title" className={styles.sectionTitle}>{t.overview.usage}</h2>
        {usage.isPending && <Loading />}
        {usage.error && <ErrorBlock error={usage.error} onRetry={() => void usage.refetch()} />}
        {usage.data && <UsageSection usage={usage.data} />}
      </section>
    </>
  );
}
