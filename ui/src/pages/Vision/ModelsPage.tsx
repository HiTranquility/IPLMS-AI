import {
  Activity,
  Boxes,
  CheckCircle2,
  Database,
  Eye,
  Fingerprint,
  Rocket,
  Search,
  ShieldCheck,
  X,
} from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import table from '@/components/common/Ui/data-display/table.module.css';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { ReasonAction } from '@/components/common/Ui/form/ReasonAction';
import { PageHeader } from '@/components/layout/PageHeader';
import { useSnapshots } from '@/hooks/queries/useVisionQueries';
import { useI18n } from '@/i18n/I18nProvider';
import { MemberStatCard } from '@/pages/Members/components/MemberStatCard';
import type { EvalRun, ModelStage } from '@/types/vision';
import { DASH, fmtDateTime, fmtInt, fmtPercent } from '@/utils/format';
import { extractEngineDigest, RegisterModelForm } from './components/RegisterModelForm';
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
  const [searchParams] = useSearchParams();
  const { me, models, evals, propose, promote, stepUp, canEvaluate, canPropose, canPromote } = useModelsPageContext();
  const snapshots = useSnapshots();
  const handleStepUp = (code: string, reason: string) => stepUp.mutateAsync({ code, reason });

  const initialGoldenId = searchParams.get('golden') || undefined;
  const initialTrainId = searchParams.get('train') || undefined;

  const [syncedDigest, setSyncedDigest] = useState<string | null>(null);
  const [selectedEvalId, setSelectedEvalId] = useState<string | null>(null);
  const [stageFilter, setStageFilter] = useState<'all' | ModelStage>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const modelList = models.data || [];
  const evalList = evals.data || [];
  const snapshotList = snapshots.data || [];

  const trainSnapshots = useMemo(
    () => snapshotList.filter((s) => s.kind === 'train'),
    [snapshotList],
  );
  const lockedGoldenSnapshots = useMemo(
    () => snapshotList.filter((s) => s.kind === 'golden' && s.frozen_at),
    [snapshotList],
  );
  const snapshotMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of snapshotList) map.set(s.id, s.name);
    return map;
  }, [snapshotList]);

  const doneEvalDigests = useMemo(() => {
    const set = new Set<string>();
    for (const run of evalList) {
      if (run.status === 'DONE') {
        const d = extractEngineDigest(run.engine_version);
        if (d) set.add(d);
      }
    }
    return set;
  }, [evalList]);

  const doneEvals = useMemo(() => evalList.filter((e) => e.status === 'DONE'), [evalList]);
  const bestStrictAcc = useMemo(() => {
    let best: number | null = null;
    for (const e of doneEvals) {
      const val = e.metrics?.exact_match_strict;
      if (typeof val === 'number' && (best === null || val > best)) best = val;
    }
    return best !== null ? fmtPercent(best) : DASH;
  }, [doneEvals]);

  // Model đang chạy production
  const prodModel = modelList.find((m) => m.stage === 'production');
  const candidateCount = modelList.filter((m) => m.stage === 'candidate').length;
  const proposedCount = modelList.filter((m) => m.stage === 'proposed').length;
  const verifiedModelsCount = modelList.filter((m) =>
    doneEvalDigests.has(m.sha256.slice(0, 12).toLowerCase()),
  ).length;

  const selectedEval = useMemo(
    () => evalList.find((r) => r.id === selectedEvalId) ?? null,
    [evalList, selectedEvalId],
  );

  const filteredModels = useMemo(() => {
    return modelList.filter((m) => {
      if (stageFilter !== 'all' && m.stage !== stageFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.trim().toLowerCase();
        const matchName = `${m.name}@${m.version}`.toLowerCase().includes(q);
        const matchArtifact = m.artifact_key.toLowerCase().includes(q);
        const matchSha = m.sha256.toLowerCase().includes(q);
        const matchNote = (m.note || '').toLowerCase().includes(q);
        if (!matchName && !matchArtifact && !matchSha && !matchNote) return false;
      }
      return true;
    });
  }, [modelList, stageFilter, searchQuery]);

  return (
    <>
      <PageHeader
        title={t.models.title}
        description={t.models.desc}
      />

      {/* Chu trình 4 bước MLOps & Huấn luyện Kiểm định 4-Mắt */}
      <section className={styles.pipelineCard} aria-label={t.models.pipelineTitle}>
        <div className={styles.pipelineHeader}>
          <span className={styles.pipelineTitle}>{t.models.pipelineTitle}</span>
        </div>
        <div className={styles.stepperGrid}>
          <div className={`${styles.stepCard} ${lockedGoldenSnapshots.length > 0 ? styles.stepDone : ''}`}>
            <div className={styles.stepTop}>
              <Database size={16} aria-hidden />
              <span className={styles.stepName}>{t.models.step1Title}</span>
            </div>
            <div className={styles.stepMeta}>
              {t.models.step1Desc(trainSnapshots.length, lockedGoldenSnapshots.length)}
            </div>
            <Link to="/vision/datasets" className={styles.stepLink}>
              {t.models.step1Link}
            </Link>
          </div>

          <div className={`${styles.stepCard} ${doneEvals.length > 0 ? styles.stepDone : ''}`}>
            <div className={styles.stepTop}>
              <Activity size={16} aria-hidden />
              <span className={styles.stepName}>{t.models.step2Title}</span>
            </div>
            <div className={styles.stepMeta}>
              {t.models.step2Desc(doneEvals.length, bestStrictAcc)}
            </div>
          </div>

          <div className={`${styles.stepCard} ${modelList.length > 0 ? styles.stepDone : ''}`}>
            <div className={styles.stepTop}>
              <Boxes size={16} aria-hidden />
              <span className={styles.stepName}>{t.models.step3Title}</span>
            </div>
            <div className={styles.stepMeta}>
              {t.models.step3Desc(candidateCount, proposedCount, verifiedModelsCount)}
            </div>
          </div>

          <div className={`${styles.stepCard} ${prodModel ? styles.stepDone : ''}`}>
            <div className={styles.stepTop}>
              <Rocket size={16} aria-hidden />
              <span className={styles.stepName}>{t.models.step4Title}</span>
            </div>
            <div className={styles.stepMeta}>
              {t.models.step4Desc(prodModel ? `${prodModel.name} v${prodModel.version}` : t.models.statProdNone)}
            </div>
          </div>
        </div>
      </section>

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
          subtext={`${candidateCount} candidate`}
        />
        <MemberStatCard
          icon={<Activity size={22} />}
          label={t.models.statEvals}
          value={evalList.length}
          tone="accent"
          subtext={t.models.statEvalsDone(doneEvals.length)}
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
                {t.models.prodRunning} {prodModel.name} <span className={styles.prodVer}>({prodModel.version})</span>
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

      {/* Đăng ký Model mới (có Presets & Đồng bộ Digest) */}
      {canPropose && (
        <section className={styles.section}>
          <RegisterModelForm
            trainSnapshots={trainSnapshots.length > 0 ? trainSnapshots : undefined}
            initialTrainSnapshotId={initialTrainId}
            latestEvalDigest={syncedDigest}
          />
        </section>
      )}

      {/* Bắt đầu đo kiểm Eval */}
      {canEvaluate && (
        <section className={styles.section}>
          <StartEvalForm
            initialSnapshotId={initialGoldenId}
            onSelectEngineDigest={(digest) => setSyncedDigest(digest)}
          />
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
                    <th scope="col" className={styles.colRight}>{t.common.actions}</th>
                  </tr>
                </thead>
                <tbody>
                  {evals.data.map((run) => {
                    const runDigest = extractEngineDigest(run.engine_version) || 'e3b0c44298fc';
                    const isSelected = selectedEvalId === run.id;
                    return (
                      <tr
                        key={run.id}
                        className={`${styles.interactiveRow} ${isSelected ? styles.interactiveRowActive : ''}`}
                        onClick={() => setSelectedEvalId(isSelected ? null : run.id)}
                      >
                        <td className={table.num}>{fmtDateTime(run.started_at)}</td>
                        <td className={styles.boldCell}>{run.snapshot_name}</td>
                        <td>
                          <Badge tone={EVAL_TONE[run.status]}>{run.status}</Badge>
                          {run.error && <div className={table.muted}>{run.error}</div>}
                        </td>
                        <td className={table.mono}>{run.engine_version || DASH}</td>
                        <td className={table.num}>{fmtInt(run.metrics?.total ?? null)}</td>
                        <td className={table.num}>{metric(run, 'exact_match_relaxed')}</td>
                        <td className={`${table.num} ${styles.strictCell}`}>
                          {metric(run, 'exact_match_strict')}
                        </td>
                        <td className={table.num}>{metric(run, 'mean_cer')}</td>
                        <td className={styles.colRight} onClick={(e) => e.stopPropagation()}>
                          <div className={styles.rowActions}>
                            <button
                              type="button"
                              className={styles.inlineBtn}
                              onClick={() => setSelectedEvalId(isSelected ? null : run.id)}
                            >
                              <Eye size={12} aria-hidden />
                              {t.models.inspectEvalBtn}
                            </button>
                            {canPropose && (
                              <button
                                type="button"
                                className={`${styles.inlineBtn} ${styles.inlineBtnAccent}`}
                                onClick={() => setSyncedDigest(runDigest)}
                              >
                                <Fingerprint size={12} aria-hidden />
                                {t.models.useDigestBtn}
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {selectedEval && (
              <div className={styles.evalInspector}>
                <div className={styles.evalInspectorHeader}>
                  <span className={styles.evalInspectorTitle}>
                    {t.models.evalDetailTitle} · <code>{selectedEval.snapshot_name}</code>
                  </span>
                  <button
                    type="button"
                    className={styles.inlineBtn}
                    onClick={() => setSelectedEvalId(null)}
                  >
                    <X size={12} aria-hidden />
                    {t.models.evalDetailClose}
                  </button>
                </div>
                <div className={styles.evalInspectorGrid}>
                  <div className={styles.evalStatItem}>
                    <span className={styles.evalStatLabel}>{t.models.strict}</span>
                    <strong className={styles.evalStatVal}>{metric(selectedEval, 'exact_match_strict')}</strong>
                  </div>
                  <div className={styles.evalStatItem}>
                    <span className={styles.evalStatLabel}>{t.models.relaxed}</span>
                    <strong className={styles.evalStatVal}>{metric(selectedEval, 'exact_match_relaxed')}</strong>
                  </div>
                  <div className={styles.evalStatItem}>
                    <span className={styles.evalStatLabel}>{t.models.cer}</span>
                    <strong className={styles.evalStatVal}>{metric(selectedEval, 'mean_cer')}</strong>
                  </div>
                  <div className={styles.evalStatItem}>
                    <span className={styles.evalStatLabel}>{t.models.evalSnapshotId}</span>
                    <code className={styles.evalStatCode}>{selectedEval.snapshot_id}</code>
                  </div>
                  <div className={styles.evalStatItem}>
                    <span className={styles.evalStatLabel}>{t.models.evalEngineDigest}</span>
                    <code className={styles.evalStatCode}>
                      {extractEngineDigest(selectedEval.engine_version) || DASH}
                    </code>
                  </div>
                  <div className={styles.evalStatItem}>
                    <span className={styles.evalStatLabel}>{t.models.evalStartedBy}</span>
                    <span className={styles.evalStatCode}>
                      {selectedEval.started_by} · {selectedEval.finished_at ? fmtDateTime(selectedEval.finished_at) : DASH}
                    </span>
                  </div>
                </div>
              </div>
            )}
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
            <div className={styles.tableToolbar}>
              <div className={styles.filterPills} role="group" aria-label={t.common.status}>
                <button
                  type="button"
                  className={`${styles.filterPill} ${stageFilter === 'all' ? styles.filterPillActive : ''}`}
                  onClick={() => setStageFilter('all')}
                >
                  {t.models.filterStageAll(modelList.length)}
                </button>
                <button
                  type="button"
                  className={`${styles.filterPill} ${stageFilter === 'production' ? styles.filterPillActive : ''}`}
                  onClick={() => setStageFilter('production')}
                >
                  {t.models.filterStageProd(modelList.filter((m) => m.stage === 'production').length)}
                </button>
                <button
                  type="button"
                  className={`${styles.filterPill} ${stageFilter === 'proposed' ? styles.filterPillActive : ''}`}
                  onClick={() => setStageFilter('proposed')}
                >
                  {t.models.filterStageProposed(proposedCount)}
                </button>
                <button
                  type="button"
                  className={`${styles.filterPill} ${stageFilter === 'candidate' ? styles.filterPillActive : ''}`}
                  onClick={() => setStageFilter('candidate')}
                >
                  {t.models.filterStageCandidate(candidateCount)}
                </button>
              </div>

              <div className={styles.searchWrap}>
                <Search size={14} aria-hidden className={styles.searchIcon} />
                <input
                  type="search"
                  className={styles.searchInput}
                  placeholder={t.models.searchModelPlaceholder}
                  aria-label={t.models.searchModelPlaceholder}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            <div className={table.wrap}>
              <table className={table.table}>
                <thead>
                  <tr>
                    <th scope="col">Model</th>
                    <th scope="col">{t.common.status}</th>
                    <th scope="col">Checksum sha256</th>
                    <th scope="col">{t.models.proposedApproved}</th>
                    <th scope="col" className={styles.colRight}>{t.common.actions}</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredModels.map((m) => {
                    const digest12 = m.sha256.slice(0, 12).toLowerCase();
                    const isEvalVerified = doneEvalDigests.has(digest12);
                    const trainSnapName = m.train_snapshot_id
                      ? snapshotMap.get(m.train_snapshot_id) || m.train_snapshot_id.slice(0, 8)
                      : null;

                    return (
                      <tr key={m.id}>
                        <td>
                          <div className={styles.modelPrimary}>
                            {m.name}@{m.version}
                          </div>
                          <div className={`${table.mono} ${styles.modelSub}`}>
                            {m.artifact_key}
                          </div>
                          {trainSnapName && (
                            <div className={styles.modelTags}>
                              <Badge tone="neutral">{t.models.linkedTrainSnapshot(trainSnapName)}</Badge>
                            </div>
                          )}
                        </td>
                        <td>
                          <Badge tone={STAGE_TONE[m.stage]}>{t.vision.stage[m.stage]}</Badge>
                        </td>
                        <td className={table.mono} title={m.sha256}>
                          <div>{m.sha256.slice(0, 16)}...</div>
                          {doneEvalDigests.size > 0 && (
                            <div className={styles.modelTags}>
                              <Badge tone={isEvalVerified ? 'success' : 'neutral'}>
                                {isEvalVerified ? t.models.evalVerifiedBadge : t.models.evalUnverifiedBadge}
                              </Badge>
                            </div>
                          )}
                        </td>
                        <td className={table.muted}>
                          {m.proposed_by ? `${m.proposed_by} · ${fmtDateTime(m.proposed_at!)}` : DASH}
                          {m.approved_by && <div>{t.models.approvedBy(m.approved_by, fmtDateTime(m.approved_at!))}</div>}
                        </td>
                        <td className={styles.colRight}>
                          {m.stage === 'candidate' && (
                            canPropose ? (
                              <ReasonAction
                                label={t.common.propose}
                                onStepUp={handleStepUp}
                                onSubmit={(reason) => propose.mutateAsync({ id: m.id, reason })}
                              />
                            ) : (
                              <Badge tone="neutral">{t.models.candidateReadOnlyBadge}</Badge>
                            )
                          )}
                          {m.stage === 'proposed' && (
                            canPromote ? (
                              <ReasonAction
                                label={t.models.promote}
                                variant="accent"
                                disabled={m.proposed_by_id === me.data?.member_id}
                                disabledHint={t.models.selfProposed}
                                onStepUp={handleStepUp}
                                onSubmit={(reason) => promote.mutateAsync({ id: m.id, reason })}
                              />
                            ) : (
                              <Badge tone="warning">{t.models.awaitingLeadApproval}</Badge>
                            )
                          )}
                          {m.stage === 'production' && (
                            <Badge tone="success">{t.models.activeProductionBadge}</Badge>
                          )}
                          {m.stage === 'retired' && (
                            <Badge tone="neutral">{t.models.retiredStatusBadge}</Badge>
                          )}
                        </td>
                      </tr>
                    );
                  })}
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
