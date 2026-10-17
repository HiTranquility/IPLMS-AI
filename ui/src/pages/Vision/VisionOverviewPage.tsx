import { useState, type FormEvent } from 'react';
import type { AccuracyReport } from '@/api/types';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { Stat } from '@/components/common/Ui/data-display/Stat';
import table from '@/components/common/Ui/data-display/table.module.css';
import { ThresholdCurve } from '@/components/common/Ui/data-display/ThresholdCurve';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { TextField } from '@/components/common/Ui/form/Field';
import { ReasonAction } from '@/components/common/Ui/form/ReasonAction';
import { PageHeader } from '@/components/layout/PageHeader';
import { useCan, useMe } from '@/hooks/useConsole';
import { useAccuracy, useDecidePolicy, usePolicies, useProposePolicy, useVisionStatus } from '@/hooks/useVision';
import { DASH, fmtDateTime, fmtInt, fmtPercent } from '@/utils/format';
import { POLICY_LABEL, POLICY_TONE } from './labels';
import styles from './vision.module.css';

const SHOWN_THRESHOLDS = new Set([0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99]);

function AccuracySection({ report }: { report: AccuracyReport }) {
  const rows = report.curve.filter((p) => SHOWN_THRESHOLDS.has(p.threshold) || p.threshold === report.suggested_threshold);
  return (
    <>
      <dl className={styles.stats}>
        <Stat
          label="Máy đọc đúng (tập bốc ngẫu nhiên)"
          value={fmtPercent(report.accuracy)}
          hint={report.interval_95 ? `95%: ${fmtPercent(report.interval_95[0])} – ${fmtPercent(report.interval_95[1])}` : 'Chưa có mẫu'}
        />
        <Stat label="Mẫu audit có nhãn người" value={fmtInt(report.total)} hint={`${fmtInt(report.truth_sources.console)} console · ${fmtInt(report.truth_sources.moderator)} moderator`} />
        <Stat label="Ngưỡng đề xuất" value={report.suggested_threshold?.toFixed(2) ?? DASH} hint={report.suggestion_reason} />
      </dl>
      {report.total > 0 && <ThresholdCurve curve={report.curve} suggested={report.suggested_threshold} target={report.target} />}
      {report.total > 0 && (
        <div className={table.wrap}>
          <table className={table.table}>
            <thead>
              <tr>
                <th scope="col" className={table.num}>Ngưỡng</th>
                <th scope="col" className={table.num}>Mẫu ≥ ngưỡng</th>
                <th scope="col" className={table.num}>Đúng</th>
                <th scope="col" className={table.num}>Tự nhận được</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((p) => (
                <tr key={p.threshold}>
                  <td className={table.num}>
                    {p.threshold.toFixed(2)} {p.threshold === report.suggested_threshold && <Badge tone="accent">đề xuất</Badge>}
                  </td>
                  <td className={table.num}>{fmtInt(p.total)}</td>
                  <td className={table.num}>{fmtPercent(p.accuracy)}</td>
                  <td className={table.num}>{fmtPercent(p.coverage)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function ProposePolicy({ suggested }: { suggested: number | null }) {
  const propose = useProposePolicy();
  const [threshold, setThreshold] = useState(String(suggested ?? 0.9));
  const [auditRate, setAuditRate] = useState('3');
  const [reason, setReason] = useState('');

  const submit = (event: FormEvent) => {
    event.preventDefault();
    propose.mutate(
      { threshold: Number(threshold), auditRate: Number(auditRate) / 100, reason: reason.trim() },
      { onSuccess: () => setReason('') },
    );
  };

  return (
    <form className={styles.panel} onSubmit={submit} aria-labelledby="propose-title">
      <h2 id="propose-title" className={styles.sectionTitle}>Đề xuất ngưỡng mới</h2>
      <div className={styles.formGrid}>
        <TextField label="Ngưỡng tự nhận" type="number" min={0.5} max={0.99} step={0.01} required value={threshold} onChange={(e) => setThreshold(e.target.value)} />
        <TextField label="Bốc kiểm ngẫu nhiên (%)" type="number" min={1} max={50} step={0.5} required value={auditRate} onChange={(e) => setAuditRate(e.target.value)} />
        <TextField label="Lý do" required minLength={3} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
        <Button type="submit" loading={propose.isPending}>Đề xuất</Button>
      </div>
      <p className={styles.note}>Số đo lúc đề xuất được lưu kèm để người duyệt thấy đúng bằng chứng.</p>
      {propose.error && <ErrorBlock error={propose.error} />}
    </form>
  );
}

export function VisionOverviewPage() {
  const me = useMe();
  const status = useVisionStatus();
  const accuracy = useAccuracy();
  const policies = usePolicies();
  const decide = useDecidePolicy();
  const canPropose = useCan('ai:model:propose');
  const canDecide = useCan('ai:policy:threshold');

  return (
    <>
      <PageHeader
        title="Tổng quan Vision"
        description="“Máy đúng bao nhiêu %” chỉ tính trên mẫu bốc ngẫu nhiên đã có nhãn người — tập kém tự tin cố tình lệch xấu nên không dùng."
      />
      <section className={styles.section} aria-labelledby="acc-title">
        <h2 id="acc-title" className={styles.sectionTitle}>Độ chính xác thật của ANPR</h2>
        {accuracy.isPending && <Loading />}
        {accuracy.error && <ErrorBlock error={accuracy.error} onRetry={() => void accuracy.refetch()} />}
        {accuracy.data && <AccuracySection report={accuracy.data} />}
      </section>

      <section className={styles.section} aria-labelledby="policy-title">
        <h2 id="policy-title" className={styles.sectionTitle}>Ngưỡng tự nhận (accept policy)</h2>
        <p className={styles.note}>Backend kéo bản đã duyệt gần nhất mỗi chu kỳ xuất A2 (mặc định 10 phút) rồi áp vào ngưỡng đang chạy; khi kênh console bật, platform không sửa được hai số này nữa.</p>
        {canPropose && accuracy.data && <ProposePolicy suggested={accuracy.data.suggested_threshold} />}
        {policies.isPending && <Loading />}
        {policies.error && <ErrorBlock error={policies.error} onRetry={() => void policies.refetch()} />}
        {policies.data?.length === 0 && <EmptyState title="Chưa có đề xuất ngưỡng nào" />}
        {policies.data && policies.data.length > 0 && (
          <div className={table.wrap}>
            <table className={table.table}>
              <thead>
                <tr>
                  <th scope="col" className={table.num}>Bản</th>
                  <th scope="col" className={table.num}>Ngưỡng</th>
                  <th scope="col" className={table.num}>Bốc kiểm</th>
                  <th scope="col">Bằng chứng lúc đề xuất</th>
                  <th scope="col">Trạng thái</th>
                  <th scope="col">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {policies.data.map((p) => (
                  <tr key={p.id}>
                    <td className={table.num}>v{p.version}</td>
                    <td className={table.num}>{p.auto_accept_threshold.toFixed(2)}</td>
                    <td className={table.num}>{fmtPercent(p.audit_rate)}</td>
                    <td className={table.muted}>
                      {p.evidence.at_threshold
                        ? `${fmtInt(p.evidence.at_threshold.total)} mẫu ≥ ngưỡng, đúng ${fmtPercent(p.evidence.at_threshold.accuracy)}`
                        : DASH}
                      <div>{p.reason} — {p.proposed_by} · {fmtDateTime(p.proposed_at)}</div>
                    </td>
                    <td>
                      <Badge tone={POLICY_TONE[p.status]}>{POLICY_LABEL[p.status]}</Badge>
                      {p.decided_by && <div className={table.muted}>{p.decided_by}</div>}
                    </td>
                    <td>
                      {p.status === 'PROPOSED' && canDecide && (
                        <div className={styles.actions}>
                          <ReasonAction
                            label="Duyệt"
                            variant="accent"
                            disabled={p.proposed_by_id === me.data?.member_id}
                            disabledHint="Cần AI Lead khác người đề xuất."
                            onSubmit={(note) => decide.mutateAsync({ id: p.id, decision: 'APPROVED', note })}
                          />
                          <ReasonAction label="Từ chối" variant="danger" onSubmit={(note) => decide.mutateAsync({ id: p.id, decision: 'REJECTED', note })} />
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className={styles.section} aria-labelledby="import-title">
        <h2 id="import-title" className={styles.sectionTitle}>Dữ liệu nhận từ backend (A2)</h2>
        {status.isPending && <Loading />}
        {status.error && <ErrorBlock error={status.error} onRetry={() => void status.refetch()} />}
        {status.data && (
          <>
            <dl className={styles.stats}>
              <Stat label="Mẫu trong console" value={fmtInt(status.data.sample_count)} hint={status.data.last_imported_at ? `nhận lần cuối ${fmtDateTime(status.data.last_imported_at)}` : 'Chưa nhận lần nào'} />
              <Stat label="Chờ duyệt" value={fmtInt(status.data.pending_review)} />
              <Stat label="Đã duyệt" value={fmtInt(status.data.approved)} />
              <Stat label="Bị trả lại" value={fmtInt(status.data.rejected)} />
            </dl>
            {status.data.recent_errors.length > 0 && (
              <div className={table.wrap}>
                <table className={table.table}>
                  <caption className="visually-hidden">Lỗi nhận gần nhất</caption>
                  <thead>
                    <tr>
                      <th scope="col">Lúc</th>
                      <th scope="col">Mẫu</th>
                      <th scope="col">Lỗi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {status.data.recent_errors.map((e) => (
                      <tr key={`${e.capture_id}-${e.at}`}>
                        <td className={table.num}>{fmtDateTime(e.at)}</td>
                        <td className={table.mono}>{e.capture_id}</td>
                        <td>{e.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>
    </>
  );
}
