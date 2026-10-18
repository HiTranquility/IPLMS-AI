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
import { useI18n } from '@/i18n/I18nProvider';
import type { Messages } from '@/i18n/vi';
import { DASH, fmtDateTime, fmtInt, fmtPercent } from '@/utils/format';
import { POLICY_TONE } from './labels';
import styles from './vision.module.css';

const SHOWN_THRESHOLDS = new Set([0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99]);

/** Lý do ngưỡng đề xuất dựng từ số liệu (cùng luật `audit_accuracy.py`) để hiện đúng ngôn ngữ đang dùng. */
function suggestionReason(report: AccuracyReport, t: Messages): string {
  const target = fmtPercent(report.target);
  if (report.total < report.min_samples) return t.visionOverview.reasonFew(report.min_samples, report.total);
  if (report.suggested_threshold === null) return t.visionOverview.reasonNone(target, report.min_samples);
  return t.visionOverview.reasonOk(target, report.min_samples);
}

function AccuracySection({ report }: { report: AccuracyReport }) {
  const { t } = useI18n();
  const rows = report.curve.filter((p) => SHOWN_THRESHOLDS.has(p.threshold) || p.threshold === report.suggested_threshold);
  return (
    <>
      <dl className={styles.stats}>
        <Stat
          label={t.visionOverview.machineAccuracy}
          value={fmtPercent(report.accuracy)}
          hint={report.interval_95 ? t.visionOverview.interval(fmtPercent(report.interval_95[0]), fmtPercent(report.interval_95[1])) : t.visionOverview.noSamples}
        />
        <Stat
          label={t.visionOverview.auditSamples}
          value={fmtInt(report.total)}
          hint={t.visionOverview.sources(fmtInt(report.truth_sources.console), fmtInt(report.truth_sources.moderator))}
        />
        <Stat label={t.visionOverview.suggested} value={report.suggested_threshold?.toFixed(2) ?? DASH} hint={suggestionReason(report, t)} />
      </dl>
      {report.total > 0 && <ThresholdCurve curve={report.curve} suggested={report.suggested_threshold} target={report.target} />}
      {report.total > 0 && (
        <div className={table.wrap}>
          <table className={table.table}>
            <thead>
              <tr>
                <th scope="col" className={table.num}>{t.visionOverview.threshold}</th>
                <th scope="col" className={table.num}>{t.visionOverview.aboveThreshold}</th>
                <th scope="col" className={table.num}>{t.visionOverview.correct}</th>
                <th scope="col" className={table.num}>{t.visionOverview.autoAccepted}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((p) => (
                <tr key={p.threshold}>
                  <td className={table.num}>
                    {p.threshold.toFixed(2)} {p.threshold === report.suggested_threshold && <Badge tone="accent">{t.visionOverview.suggestedBadge}</Badge>}
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
  const { t } = useI18n();
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
      <h2 id="propose-title" className={styles.sectionTitle}>{t.visionOverview.proposeTitle}</h2>
      <div className={styles.formGrid}>
        <TextField label={t.visionOverview.thresholdField} type="number" min={0.5} max={0.99} step={0.01} required value={threshold} onChange={(e) => setThreshold(e.target.value)} />
        <TextField label={t.visionOverview.auditRateField} type="number" min={1} max={50} step={0.5} required value={auditRate} onChange={(e) => setAuditRate(e.target.value)} />
        <TextField label={t.common.reason} required minLength={3} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
        <Button type="submit" loading={propose.isPending}>{t.common.propose}</Button>
      </div>
      <p className={styles.note}>{t.visionOverview.proposeNote}</p>
      {propose.error && <ErrorBlock error={propose.error} />}
    </form>
  );
}

export function VisionOverviewPage() {
  const { t } = useI18n();
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
        title={t.visionOverview.title}
        description={t.visionOverview.desc}
      />
      <section className={styles.section} aria-labelledby="acc-title">
        <h2 id="acc-title" className={styles.sectionTitle}>{t.visionOverview.accuracyTitle}</h2>
        {accuracy.isPending && <Loading />}
        {accuracy.error && <ErrorBlock error={accuracy.error} onRetry={() => void accuracy.refetch()} />}
        {accuracy.data && <AccuracySection report={accuracy.data} />}
      </section>

      <section className={styles.section} aria-labelledby="policy-title">
        <h2 id="policy-title" className={styles.sectionTitle}>{t.visionOverview.policyTitle}</h2>
        <p className={styles.note}>{t.visionOverview.policyNote}</p>
        {canPropose && accuracy.data && <ProposePolicy suggested={accuracy.data.suggested_threshold} />}
        {policies.isPending && <Loading />}
        {policies.error && <ErrorBlock error={policies.error} onRetry={() => void policies.refetch()} />}
        {policies.data?.length === 0 && <EmptyState title={t.visionOverview.noPolicies} />}
        {policies.data && policies.data.length > 0 && (
          <div className={table.wrap}>
            <table className={table.table}>
              <thead>
                <tr>
                  <th scope="col" className={table.num}>{t.visionOverview.version}</th>
                  <th scope="col" className={table.num}>{t.visionOverview.threshold}</th>
                  <th scope="col" className={table.num}>{t.visionOverview.auditRate}</th>
                  <th scope="col">{t.visionOverview.evidence}</th>
                  <th scope="col">{t.common.status}</th>
                  <th scope="col">{t.common.actions}</th>
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
                        ? t.visionOverview.evidenceAt(fmtInt(p.evidence.at_threshold.total), fmtPercent(p.evidence.at_threshold.accuracy))
                        : DASH}
                      <div>{p.reason} — {p.proposed_by} · {fmtDateTime(p.proposed_at)}</div>
                    </td>
                    <td>
                      <Badge tone={POLICY_TONE[p.status]}>{t.vision.policy[p.status]}</Badge>
                      {p.decided_by && <div className={table.muted}>{p.decided_by}</div>}
                    </td>
                    <td>
                      {p.status === 'PROPOSED' && canDecide && (
                        <div className={styles.actions}>
                          <ReasonAction
                            label={t.common.approve}
                            variant="accent"
                            disabled={p.proposed_by_id === me.data?.member_id}
                            disabledHint={t.visionOverview.fourEyes}
                            onSubmit={(note) => decide.mutateAsync({ id: p.id, decision: 'APPROVED', note })}
                          />
                          <ReasonAction label={t.common.reject} variant="danger" onSubmit={(note) => decide.mutateAsync({ id: p.id, decision: 'REJECTED', note })} />
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
        <h2 id="import-title" className={styles.sectionTitle}>{t.visionOverview.importTitle}</h2>
        {status.isPending && <Loading />}
        {status.error && <ErrorBlock error={status.error} onRetry={() => void status.refetch()} />}
        {status.data && (
          <>
            <dl className={styles.stats}>
              <Stat
                label={t.visionOverview.samplesInConsole}
                value={fmtInt(status.data.sample_count)}
                hint={status.data.last_imported_at ? t.visionOverview.lastImported(fmtDateTime(status.data.last_imported_at)) : t.visionOverview.neverImported}
              />
              <Stat label={t.visionOverview.pending} value={fmtInt(status.data.pending_review)} />
              <Stat label={t.visionOverview.approved} value={fmtInt(status.data.approved)} />
              <Stat label={t.visionOverview.rejected} value={fmtInt(status.data.rejected)} />
            </dl>
            {status.data.recent_errors.length > 0 && (
              <div className={table.wrap}>
                <table className={table.table}>
                  <caption className="visually-hidden">{t.visionOverview.importErrors}</caption>
                  <thead>
                    <tr>
                      <th scope="col">{t.common.at}</th>
                      <th scope="col">{t.visionOverview.captureId}</th>
                      <th scope="col">{t.common.error}</th>
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
