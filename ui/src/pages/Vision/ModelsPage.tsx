import { Activity, Boxes, CheckCircle2, Rocket, ShieldCheck } from 'lucide-react';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import table from '@/components/common/Ui/data-display/table.module.css';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { ReasonAction } from '@/components/common/Ui/form/ReasonAction';
import { PageHeader } from '@/components/layout/PageHeader';
import { useI18n } from '@/i18n/I18nProvider';
import { MemberStatCard } from '@/pages/Members/components/MemberStatCard';
import type { EvalRun } from '@/types/vision';
import { DASH, fmtDateTime, fmtInt, fmtPercent } from '@/utils/format';
import { RegisterModelForm } from './components/RegisterModelForm';
import { StartEvalForm } from './components/StartEvalForm';
import { STAGE_TONE } from './labels';
import { ModelsPageProvider, useModelsPageContext } from './ModelsPageContext';
import styles from './ModelsPage.module.css';

const EVAL_TONE = { RUNNING: 'warning', DONE: 'success', FAILED: 'danger' } as const;

function metric(run: EvalRun, key: 'exact_match_relaxed' | 'exact_match_strict' | 'mean_cer') {
  const value = run.metrics?.[key];
  return typeof value === 'number' ? (key === 'mean_cer' ? value.toFixed(3) : fmtPercent(value)) : DASH;
}

function ModelsPageContent() {
  const { t } = useI18n();
  const { me, models, evals, propose, promote, stepUp, canEvaluate, canPropose, canPromote } = useModelsPageContext();
  const handleStepUp = (code: string, reason: string) => stepUp.mutateAsync({ code, reason });

  const modelList = models.data || [];
  const evalList = evals.data || [];

  // Model đang chạy production
  const prodModel = modelList.find((m) => m.stage === 'production');
  const proposedCount = modelList.filter((m) => m.stage === 'proposed').length;

  return (
    <>
      <PageHeader
        title={t.models.title}
        description={t.models.desc}
      />

      {/* 4 Thẻ chỉ số tổng quan MLOps */}
      <div className={styles.statsGrid}>
        <MemberStatCard
          icon={<Rocket size={22} />}
          label={t.models.statProd}
          value={prodModel ? `${prodModel.name}@${prodModel.version}` : t.models.statProdNone}
          tone="success"
          subtext={prodModel ? t.models.statProdBy(prodModel.approved_by || 'Lead') : t.models.statProdNeed}
        />
        <MemberStatCard
          icon={<Boxes size={22} />}
          label={t.models.statTotal}
          value={modelList.length}
          tone="primary"
          subtext={`${modelList.filter((m) => m.stage === 'candidate').length} candidate`}
        />
        <MemberStatCard
          icon={<Activity size={22} />}
          label={t.models.statEvals}
          value={evalList.length}
          tone="accent"
          subtext={t.models.statEvalsDone(evalList.filter((e) => e.status === 'DONE').length)}
        />
        <MemberStatCard
          icon={<ShieldCheck size={22} />}
          label={t.models.statPending}
          value={proposedCount}
          tone="warning"
          subtext={proposedCount > 0 ? t.models.statPendingSub : t.models.statPendingNone}
        />
      </div>

      {/* Production Hero Card */}
      {prodModel && (
        <div className={styles.prodCard}>
          <div className={styles.prodInfo}>
            <span className={styles.prodDot} />
            <div>
              <div className={styles.prodName}>
                {t.models.prodRunning} {prodModel.name} <span style={{ fontWeight: 400 }}>({prodModel.version})</span>
              </div>
              <div className={styles.prodMeta}>
                Artifact: <code>{prodModel.artifact_key}</code> · {t.models.prodApprovedAt(fmtDateTime(prodModel.approved_at || prodModel.registered_at))}
              </div>
            </div>
          </div>
          <Badge tone="success">
            <CheckCircle2 size={12} aria-hidden />
            {t.models.prodServing}
          </Badge>
        </div>
      )}

      {/* Đăng ký Model mới (có Presets & Test Connection) */}
      {canPropose && (
        <section className={styles.section}>
          <RegisterModelForm />
        </section>
      )}

      {/* Bắt đầu đo kiểm Eval */}
      {canEvaluate && (
        <section className={styles.section}>
          <StartEvalForm />
        </section>
      )}

      {/* Bảng kết quả Benchmark Eval */}
      <section className={styles.section} aria-labelledby="evals-title">
        <h2 id="evals-title" className={styles.sectionTitle}>{t.models.evalsTitle}</h2>
        {evals.isPending && <Loading />}
        {evals.error && <ErrorBlock error={evals.error} onRetry={() => void evals.refetch()} />}
        {evals.data?.length === 0 && <EmptyState title={t.models.noEvals} />}
        {evals.data && evals.data.length > 0 && (
          <div className={styles.tableCard}>
            <div className={table.wrap}>
              <table className={table.table}>
                <thead>
                  <tr>
                    <th scope="col">{t.models.started}</th>
                    <th scope="col">{t.models.goldenCol}</th>
                    <th scope="col">{t.common.status}</th>
                    <th scope="col">Engine</th>
                    <th scope="col" className={table.num}>{t.common.sample}</th>
                    <th scope="col" className={table.num}>{t.models.relaxed}</th>
                    <th scope="col" className={table.num}>{t.models.strict}</th>
                    <th scope="col" className={table.num}>{t.models.cer}</th>
                  </tr>
                </thead>
                <tbody>
                  {evals.data.map((run) => (
                    <tr key={run.id}>
                      <td className={table.num}>{fmtDateTime(run.started_at)}</td>
                      <td style={{ fontWeight: 600 }}>{run.snapshot_name}</td>
                      <td>
                        <Badge tone={EVAL_TONE[run.status]}>{run.status}</Badge>
                        {run.error && <div className={table.muted}>{run.error}</div>}
                      </td>
                      <td className={table.mono}>{run.engine_version || DASH}</td>
                      <td className={table.num}>{fmtInt(run.metrics?.total ?? null)}</td>
                      <td className={table.num}>{metric(run, 'exact_match_relaxed')}</td>
                      <td className={table.num} style={{ fontWeight: 600, color: 'var(--color-success)' }}>
                        {metric(run, 'exact_match_strict')}
                      </td>
                      <td className={table.num}>{metric(run, 'mean_cer')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      {/* Danh sách các phiên bản Model đã đăng ký */}
      <section className={styles.section} aria-labelledby="models-title">
        <h2 id="models-title" className={styles.sectionTitle}>{t.models.modelsTitle}</h2>
        {models.isPending && <Loading />}
        {models.error && <ErrorBlock error={models.error} onRetry={() => void models.refetch()} />}
        {models.data?.length === 0 && <EmptyState icon={<Boxes size={28} />} title={t.models.noModels} />}
        {models.data && models.data.length > 0 && (
          <div className={styles.tableCard}>
            <div className={table.wrap}>
              <table className={table.table}>
                <thead>
                  <tr>
                    <th scope="col">Model</th>
                    <th scope="col">{t.common.status}</th>
                    <th scope="col">Checksum sha256</th>
                    <th scope="col">{t.models.proposedApproved}</th>
                    <th scope="col" style={{ textAlign: 'right' }}>{t.common.actions}</th>
                  </tr>
                </thead>
                <tbody>
                  {models.data.map((m) => (
                    <tr key={m.id}>
                      <td>
                        <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>
                          {m.name}@{m.version}
                        </div>
                        <div className={table.mono} style={{ fontSize: '11px', color: 'var(--color-muted)' }}>
                          {m.artifact_key}
                        </div>
                      </td>
                      <td>
                        <Badge tone={STAGE_TONE[m.stage]}>{t.vision.stage[m.stage]}</Badge>
                      </td>
                      <td className={table.mono} title={m.sha256}>
                        {m.sha256.slice(0, 16)}...
                      </td>
                      <td className={table.muted}>
                        {m.proposed_by ? `${m.proposed_by} · ${fmtDateTime(m.proposed_at!)}` : DASH}
                        {m.approved_by && <div>{t.models.approvedBy(m.approved_by, fmtDateTime(m.approved_at!))}</div>}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {m.stage === 'candidate' && canPropose && (
                          <ReasonAction
                            label={t.common.propose}
                            onStepUp={handleStepUp}
                            onSubmit={(reason) => propose.mutateAsync({ id: m.id, reason })}
                          />
                        )}
                        {m.stage === 'proposed' && canPromote && (
                          <ReasonAction
                            label={t.models.promote}
                            variant="accent"
                            disabled={m.proposed_by_id === me.data?.member_id}
                            disabledHint={t.models.selfProposed}
                            onStepUp={handleStepUp}
                            onSubmit={(reason) => promote.mutateAsync({ id: m.id, reason })}
                          />
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
    </>
  );
}

export function ModelsPage() {
  return (
    <ModelsPageProvider>
      <ModelsPageContent />
    </ModelsPageProvider>
  );
}

export default ModelsPage;
