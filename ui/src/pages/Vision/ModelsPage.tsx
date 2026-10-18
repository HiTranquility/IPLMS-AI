import { Boxes } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import type { EvalRun } from '@/api/types';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import table from '@/components/common/Ui/data-display/table.module.css';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { SelectField, TextField } from '@/components/common/Ui/form/Field';
import { ReasonAction } from '@/components/common/Ui/form/ReasonAction';
import { PageHeader } from '@/components/layout/PageHeader';
import { useCan, useMe } from '@/hooks/useConsole';
import { useEvals, useModels, usePromoteModel, useProposeModel, useRegisterModel, useSnapshots, useStartEval } from '@/hooks/useVision';
import { useI18n } from '@/i18n/I18nProvider';
import { DASH, fmtDateTime, fmtInt, fmtPercent } from '@/utils/format';
import { STAGE_TONE } from './labels';
import styles from './vision.module.css';

const EVAL_TONE = { RUNNING: 'warning', DONE: 'success', FAILED: 'danger' } as const;

function StartEval() {
  const { t } = useI18n();
  const snapshots = useSnapshots();
  const start = useStartEval();
  const [snapshotId, setSnapshotId] = useState('');
  const frozen = snapshots.data?.filter((s) => s.kind === 'golden' && s.frozen_at) ?? [];

  const submit = (event: FormEvent) => {
    event.preventDefault();
    start.mutate(snapshotId);
  };

  return (
    <form className={styles.panel} onSubmit={submit} aria-labelledby="eval-title">
      <h2 id="eval-title" className={styles.sectionTitle}>{t.models.evalTitle}</h2>
      <p className={styles.note}>{t.models.evalNote}</p>
      {snapshots.error && <ErrorBlock error={snapshots.error} />}
      <div className={styles.formGrid}>
        <SelectField label={t.models.frozenGolden} required value={snapshotId} onChange={(e) => setSnapshotId(e.target.value)}>
          <option value="">{frozen.length ? t.models.pickGolden : t.models.noGolden}</option>
          {frozen.map((s) => <option key={s.id} value={s.id}>{t.models.goldenOption(s.name, fmtInt(s.sample_count))}</option>)}
        </SelectField>
        <Button type="submit" disabled={!snapshotId} loading={start.isPending}>{t.models.startEval}</Button>
      </div>
      {start.error && <ErrorBlock error={start.error} />}
    </form>
  );
}

function RegisterModel() {
  const { t } = useI18n();
  const register = useRegisterModel();
  const empty = { name: 'anpr-yolo', version: '', artifact_key: '', sha256: '', note: '' };
  const [form, setForm] = useState(empty);
  const set = (key: keyof typeof empty) => (e: { target: { value: string } }) => setForm({ ...form, [key]: e.target.value });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    register.mutate(form, { onSuccess: () => setForm(empty) });
  };

  return (
    <form className={styles.panel} onSubmit={submit} aria-labelledby="register-title">
      <h2 id="register-title" className={styles.sectionTitle}>{t.models.registerTitle}</h2>
      <div className={styles.formGrid}>
        <TextField label={t.common.name} required value={form.name} onChange={set('name')} />
        <TextField label={t.models.version} required maxLength={64} value={form.version} onChange={set('version')} />
        <TextField label="artifact_key" hint={t.models.artifactHint} required value={form.artifact_key} onChange={set('artifact_key')} />
        <TextField label="sha256 weights" required minLength={64} maxLength={64} value={form.sha256} onChange={set('sha256')} />
        <TextField label={t.models.note} maxLength={500} value={form.note} onChange={set('note')} />
        <Button type="submit" loading={register.isPending}>{t.models.register}</Button>
      </div>
      {register.error && <ErrorBlock error={register.error} />}
    </form>
  );
}

function metric(run: EvalRun, key: 'exact_match_relaxed' | 'exact_match_strict' | 'mean_cer') {
  const value = run.metrics?.[key];
  return typeof value === 'number' ? (key === 'mean_cer' ? value.toFixed(3) : fmtPercent(value)) : DASH;
}

export function ModelsPage() {
  const { t } = useI18n();
  const me = useMe();
  const models = useModels();
  const evals = useEvals();
  const propose = useProposeModel();
  const promote = usePromoteModel();
  const canEvaluate = useCan('ai:model:evaluate');
  const canPropose = useCan('ai:model:propose');
  const canPromote = useCan('ai:model:promote');

  return (
    <>
      <PageHeader
        title={t.models.title}
        description={t.models.desc}
      />
      {canEvaluate && <section className={styles.section}><StartEval /></section>}
      <section className={styles.section} aria-labelledby="evals-title">
        <h2 id="evals-title" className={styles.sectionTitle}>{t.models.evalsTitle}</h2>
        {evals.isPending && <Loading />}
        {evals.error && <ErrorBlock error={evals.error} onRetry={() => void evals.refetch()} />}
        {evals.data?.length === 0 && <EmptyState title={t.models.noEvals} />}
        {evals.data && evals.data.length > 0 && (
          <div className={table.wrap}>
            <table className={table.table}>
              <thead>
                <tr>
                  <th scope="col">{t.models.started}</th>
                  <th scope="col">Golden</th>
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
                    <td>{run.snapshot_name}</td>
                    <td><Badge tone={EVAL_TONE[run.status]}>{run.status}</Badge>{run.error && <div className={table.muted}>{run.error}</div>}</td>
                    <td className={table.mono}>{run.engine_version || DASH}</td>
                    <td className={table.num}>{fmtInt(run.metrics?.total ?? null)}</td>
                    <td className={table.num}>{metric(run, 'exact_match_relaxed')}</td>
                    <td className={table.num}>{metric(run, 'exact_match_strict')}</td>
                    <td className={table.num}>{metric(run, 'mean_cer')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      {canPropose && <section className={styles.section}><RegisterModel /></section>}
      <section className={styles.section} aria-labelledby="models-title">
        <h2 id="models-title" className={styles.sectionTitle}>{t.models.modelsTitle}</h2>
        {models.isPending && <Loading />}
        {models.error && <ErrorBlock error={models.error} onRetry={() => void models.refetch()} />}
        {models.data?.length === 0 && <EmptyState icon={<Boxes size={28} />} title={t.models.noModels} />}
        {models.data && models.data.length > 0 && (
          <div className={table.wrap}>
            <table className={table.table}>
              <thead>
                <tr>
                  <th scope="col">Model</th>
                  <th scope="col">{t.common.status}</th>
                  <th scope="col">sha256</th>
                  <th scope="col">{t.models.proposedApproved}</th>
                  <th scope="col">{t.common.actions}</th>
                </tr>
              </thead>
              <tbody>
                {models.data.map((m) => (
                  <tr key={m.id}>
                    <td>
                      <div>{m.name}@{m.version}</div>
                      <div className={table.mono}>{m.artifact_key}</div>
                    </td>
                    <td><Badge tone={STAGE_TONE[m.stage]}>{t.vision.stage[m.stage]}</Badge></td>
                    <td className={table.mono} title={m.sha256}>{m.sha256.slice(0, 12)}</td>
                    <td className={table.muted}>
                      {m.proposed_by ? `${m.proposed_by} · ${fmtDateTime(m.proposed_at!)}` : DASH}
                      {m.approved_by && <div>{t.models.approvedBy(m.approved_by, fmtDateTime(m.approved_at!))}</div>}
                    </td>
                    <td>
                      {m.stage === 'candidate' && canPropose && (
                        <ReasonAction label={t.common.propose} onSubmit={(reason) => propose.mutateAsync({ id: m.id, reason })} />
                      )}
                      {m.stage === 'proposed' && canPromote && (
                        <ReasonAction
                          label={t.models.promote}
                          variant="accent"
                          disabled={m.proposed_by_id === me.data?.member_id}
                          disabledHint={t.models.selfProposed}
                          onSubmit={(reason) => promote.mutateAsync({ id: m.id, reason })}
                        />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
