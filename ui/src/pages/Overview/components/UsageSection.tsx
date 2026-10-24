import { Stat } from '@/components/common/Ui/data-display/Stat';
import table from '@/components/common/Ui/data-display/table.module.css';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { useI18n } from '@/i18n/I18nProvider';
import type { UsageSummary } from '@/types/copilot';
import { DASH, fmtDay, fmtInt, fmtMs, fmtPercent, fmtUsd, ratio } from '@/utils/format';
import styles from '../OverviewPage.module.css';

export interface UsageSectionProps {
  usage: UsageSummary;
}

export function UsageSection({ usage }: UsageSectionProps) {
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
        <Stat
          label={t.overview.avgSpeed}
          value={usage.avg_speed_tok_s ? `${usage.avg_speed_tok_s} tok/s` : DASH}
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
              <th scope="col" className={table.num}>{t.overview.speedCol}</th>
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
                <td className={table.num}>{day.speed_tok_s ? `${day.speed_tok_s} tok/s` : DASH}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default UsageSection;
