import { Badge } from '@/components/common/Ui/data-display/Badge';
import { Stat } from '@/components/common/Ui/data-display/Stat';
import table from '@/components/common/Ui/data-display/table.module.css';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { ReasonAction } from '@/components/common/Ui/form/ReasonAction';
import { PageHeader } from '@/components/layout/PageHeader';
import { useI18n } from '@/i18n/I18nProvider';
import { DASH, fmtDateTime, fmtInt, fmtPercent } from '@/utils/format';
import { AccuracySection } from './components/AccuracySection';
import { ProposePolicyForm } from './components/ProposePolicyForm';
import { POLICY_TONE } from './labels';
import { VisionOverviewPageProvider, useVisionOverviewPageContext } from './VisionOverviewPageContext';
import styles from './VisionOverviewPage.module.css';

function VisionOverviewPageContent() {
  const { t } = useI18n();
  const { me, status, accuracy, policies, decide, stepUp, canPropose, canDecide } = useVisionOverviewPageContext();
  const handleStepUp = (code: string, reason: string) => stepUp.mutateAsync({ code, reason });

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
        {canPropose && accuracy.data && <ProposePolicyForm suggested={accuracy.data.suggested_threshold} />}
        {policies.isPending && <Loading />}
        {policies.error && <ErrorBlock error={policies.error} onRetry={() => void policies.refetch()} />}
        {policies.data?.length === 0 && <EmptyState title={t.visionOverview.noPolicies} />}
        {policies.data && policies.data.length > 0 && (
          <div className={styles.tableCard}>
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
                            onStepUp={handleStepUp}
                            onSubmit={(note) => decide.mutateAsync({ id: p.id, decision: 'APPROVED', note })}
                          />
                          <ReasonAction
                            label={t.common.reject}
                            variant="danger"
                            onStepUp={handleStepUp}
                            onSubmit={(note) => decide.mutateAsync({ id: p.id, decision: 'REJECTED', note })}
                          />
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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

export function VisionOverviewPage() {
  return (
    <VisionOverviewPageProvider>
      <VisionOverviewPageContent />
    </VisionOverviewPageProvider>
  );
}

export default VisionOverviewPage;
