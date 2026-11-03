import { CheckCircle2, Clock, Coins, ShieldAlert } from 'lucide-react';
import { useState } from 'react';
import { Segmented } from '@/components/common/Ui/button/Segmented';
import table from '@/components/common/Ui/data-display/table.module.css';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { PageHeader } from '@/components/layout/PageHeader';
import { useReviewStats, useUsage } from '@/hooks/queries/useCopilotQueries';
import { useI18n } from '@/i18n/I18nProvider';
import { MemberStatCard } from '@/pages/Members/components/MemberStatCard';
import { DASH, fmtDay, fmtInt, fmtMs, fmtPercent, fmtUsd, ratio } from '@/utils/format';
import { DistributionSection } from './components/DistributionSection';
import { TrendChart } from './components/TrendChart';
import styles from './OverviewPage.module.css';

const WINDOWS = [7, 30, 90];

export function OverviewPage() {
  const { t } = useI18n();
  const [days, setDays] = useState(7);
  const usage = useUsage(days);
  const review = useReviewStats(days);

  const u = usage.data;
  const r = review.data;

  // Tỷ lệ thành công
  const successRate = u && u.total_requests > 0 ? ratio(u.success_requests, u.total_requests) : null;

  return (
    <div className={styles.page}>
      <PageHeader
        title={t.overview.title}
        description={t.overview.desc}
        actions={
          <Segmented
            label={t.overview.windowLabel}
            value={days}
            options={WINDOWS.map((value) => ({ value, label: t.overview.window(value) }))}
            onChange={setDays}
          />
        }
      />

      {(usage.isPending || review.isPending) && <Loading />}
      {usage.error && <ErrorBlock error={usage.error} onRetry={() => void usage.refetch()} />}
      {review.error && <ErrorBlock error={review.error} onRetry={() => void review.refetch()} />}

      {u && r && (
        <>
          {/* Hàng 4 Thẻ KPI trên cùng */}
          <div className={styles.kpiGrid}>
            <MemberStatCard
              icon={<CheckCircle2 size={20} />}
              label={t.overview.kpiSuccessRate}
              value={successRate !== null ? fmtPercent(successRate) : DASH}
              tone="success"
              subtext={t.overview.kpiTotalRequestsSub(fmtInt(u.success_requests), fmtInt(u.total_requests))}
            />
            <MemberStatCard
              icon={<ShieldAlert size={20} />}
              label={t.overview.kpiAuditedAccuracy}
              value={r.accuracy !== null ? fmtPercent(r.accuracy) : DASH}
              tone="accent"
              subtext={r.reviewed > 0 ? t.overview.reviewedHint(fmtInt(r.reviewed)) : t.overview.noReviews}
            />
            <MemberStatCard
              icon={<Clock size={20} />}
              label={t.overview.kpiP95Latency}
              value={fmtMs(u.p95_latency_ms)}
              tone="primary"
              subtext={`${t.overview.avgLatency}: ${fmtMs(u.avg_latency_ms)}`}
            />
            <MemberStatCard
              icon={<Coins size={20} />}
              label={t.overview.kpiTotalCost}
              value={u.cost_known ? fmtUsd(u.total_cost_usd) : `${fmtInt(u.input_tokens + u.output_tokens)} tok`}
              tone="warning"
              subtext={u.cost_known ? t.overview.perTurn(fmtUsd(u.avg_cost_usd)) : `${fmtInt(u.input_tokens)} in / ${fmtInt(u.output_tokens)} out`}
            />
          </div>

          {/* Biểu đồ xu hướng SVG Native */}
          <TrendChart days={u.days} />

          {/* Phân rã 3 cột: Trạng thái, Chất lượng & Tài nguyên */}
          <DistributionSection usage={u} review={r} />

          {/* Bảng phân tích chi tiết theo ngày */}
          <section className={styles.tableSection} aria-label={t.overview.byDay}>
            <div className={styles.tableHeader}>
              <h2 className={styles.tableTitle}>{t.overview.byDay}</h2>
            </div>

            {u.days.length === 0 ? (
              <EmptyState title={t.overview.emptyTitle} description={t.overview.emptyDesc} />
            ) : (
              <div className={table.wrap}>
                <table className={table.table} aria-label={t.overview.byDay}>
                  <thead>
                    <tr>
                      <th scope="col">{t.overview.day}</th>
                      <th scope="col" className={table.num}>{t.overview.turns}</th>
                      <th scope="col" className={`${table.num} ${table.toneSuccess}`}>{t.overview.answered}</th>
                      <th scope="col" className={`${table.num} ${table.toneWarning}`}>{t.overview.refusedShort}</th>
                      <th scope="col" className={`${table.num} ${table.toneDanger}`}>{t.overview.errors}</th>
                      <th scope="col" className={table.num}>{t.overview.avgLatency}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {u.days.map((day) => {
                      const success = Math.max(0, day.requests - day.refused - day.errors);
                      const speedClass =
                        day.avg_latency_ms < 500
                          ? styles.speedFast
                          : day.avg_latency_ms < 1000
                            ? styles.speedNormal
                            : styles.speedSlow;

                      return (
                        <tr key={day.date}>
                          <td className={table.mono}>{fmtDay(day.date)}</td>
                          <td className={table.numStrong}>{fmtInt(day.requests)}</td>
                          <td className={`${table.num} ${table.toneSuccess}`}>{fmtInt(success)}</td>
                          <td className={`${table.num} ${day.refused > 0 ? table.toneWarning : table.faded}`}>
                            {fmtInt(day.refused)}
                          </td>
                          <td className={`${table.num} ${day.errors > 0 ? table.toneDanger : table.faded}`}>
                            {fmtInt(day.errors)}
                          </td>
                          <td className={table.num}>
                            <span className={`${styles.speedBadge} ${speedClass}`}>
                              {fmtMs(day.avg_latency_ms)}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

export default OverviewPage;
