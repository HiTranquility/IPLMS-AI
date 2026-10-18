import { useState } from 'react';
import type { ReviewStats, UsageSummary } from '@/api/types';
import { Segmented } from '@/components/common/Ui/button/Segmented';
import { Stat } from '@/components/common/Ui/data-display/Stat';
import table from '@/components/common/Ui/data-display/table.module.css';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { PageHeader } from '@/components/layout/PageHeader';
import { useReviewStats, useUsage } from '@/hooks/useConsole';
import { DASH, fmtDay, fmtInt, fmtMs, fmtPercent, fmtUsd, ratio } from '@/utils/format';
import styles from './OverviewPage.module.css';

const WINDOWS = [
  { value: 7, label: '7 ngày' },
  { value: 30, label: '30 ngày' },
  { value: 90, label: '90 ngày' },
];

function UsageSection({ usage }: { usage: UsageSummary }) {
  if (usage.total_requests === 0) {
    return (
      <EmptyState
        title="Chưa có lượt Copilot nào trong cửa sổ này"
        description="Số liệu ghi khi người dùng hỏi Copilot qua backend. Kiểm AI_TELEMETRY_ENABLED và AI_TELEMETRY_HMAC_KEY nếu đã có người hỏi mà vẫn trống."
      />
    );
  }
  const rated = usage.thumbs_up + usage.thumbs_down;
  return (
    <>
      <dl className={styles.stats}>
        <Stat label="Lượt hỏi" value={fmtInt(usage.total_requests)} />
        <Stat label="Trả lời được" value={fmtPercent(ratio(usage.success_requests, usage.total_requests))} hint={`${fmtInt(usage.success_requests)} lượt`} />
        <Stat label="Chặn bởi guard" value={fmtInt(usage.refused_requests)} />
        <Stat label="Không có ngữ cảnh" value={fmtInt(usage.no_context_requests)} />
        <Stat label="Lỗi" value={fmtInt(usage.error_requests)} />
      </dl>
      <dl className={styles.stats}>
        <Stat label="Độ trễ TB" value={fmtMs(usage.avg_latency_ms)} />
        <Stat label="Độ trễ p95" value={fmtMs(usage.p95_latency_ms)} />
        <Stat label="Token vào / ra" value={`${fmtInt(usage.input_tokens)} / ${fmtInt(usage.output_tokens)}`} />
        <Stat
          label="Chi phí"
          value={usage.cost_known ? fmtUsd(usage.total_cost_usd) : DASH}
          hint={usage.cost_known ? `${fmtUsd(usage.avg_cost_usd)} / lượt` : 'Chưa cấu hình giá hoặc có lượt thiếu token'}
        />
        <Stat
          label="Người dùng chấm hữu ích"
          value={fmtPercent(ratio(usage.thumbs_up, rated))}
          hint={rated ? `${fmtInt(usage.thumbs_up)} hữu ích · ${fmtInt(usage.thumbs_down)} chưa đúng` : 'Chưa ai chấm'}
        />
      </dl>
      <h2 className={styles.sectionTitle}>Theo ngày (giờ Việt Nam)</h2>
      <div className={table.wrap}>
        <table className={table.table}>
          <thead>
            <tr>
              <th scope="col">Ngày</th>
              <th scope="col" className={table.num}>Lượt</th>
              <th scope="col" className={table.num}>Chặn</th>
              <th scope="col" className={table.num}>Lỗi</th>
              <th scope="col" className={table.num}>Độ trễ TB</th>
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
  return (
    <dl className={styles.stats}>
      <Stat
        label="Tỉ lệ đúng (người chấm)"
        value={fmtPercent(stats.accuracy)}
        hint={stats.reviewed ? `trên ${fmtInt(stats.reviewed)} lượt đã chấm` : 'Chưa chấm lượt nào trong Copilot Lab'}
      />
      <Stat label="Đúng" value={fmtInt(stats.correct)} />
      <Stat label="Sai" value={fmtInt(stats.incorrect)} />
      <Stat label="Không an toàn" value={fmtInt(stats.unsafe)} />
    </dl>
  );
}

export function OverviewPage() {
  const [days, setDays] = useState(7);
  const usage = useUsage(days);
  const review = useReviewStats(days);

  return (
    <>
      <PageHeader
        title="Tổng quan Copilot"
        description="Số liệu từ telemetry ai_request_log (câu chữ đã che PII). Tỉ lệ đúng chỉ tính trên lượt đã được người chấm, không suy từ nút hữu ích."
        actions={<Segmented label="Cửa sổ thống kê" value={days} options={WINDOWS} onChange={setDays} />}
      />
      <section aria-labelledby="accuracy-title" className={styles.section}>
        <h2 id="accuracy-title" className={styles.sectionTitle}>Chất lượng trả lời</h2>
        {review.isPending && <Loading />}
        {review.error && <ErrorBlock error={review.error} onRetry={() => void review.refetch()} />}
        {review.data && <AccuracySection stats={review.data} />}
      </section>
      <section aria-labelledby="usage-title" className={styles.section}>
        <h2 id="usage-title" className={styles.sectionTitle}>Mức dùng</h2>
        {usage.isPending && <Loading />}
        {usage.error && <ErrorBlock error={usage.error} onRetry={() => void usage.refetch()} />}
        {usage.data && <UsageSection usage={usage.data} />}
      </section>
    </>
  );
}
