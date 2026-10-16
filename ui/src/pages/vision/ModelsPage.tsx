import { Boxes } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import type { EvalRun } from '@/api/types';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import table from '@/components/common/Ui/data-display/Table.module.css';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { SelectField, TextField } from '@/components/common/Ui/form/Field';
import { ReasonAction } from '@/components/common/Ui/form/ReasonAction';
import { PageHeader } from '@/components/layout/PageHeader';
import { useCan, useMe } from '@/hooks/useConsole';
import { useEvals, useModels, usePromoteModel, useProposeModel, useRegisterModel, useSnapshots, useStartEval } from '@/hooks/useVision';
import { DASH, fmtDateTime, fmtInt, fmtPercent } from '@/utils/format';
import { STAGE_LABEL, STAGE_TONE } from './labels';
import styles from './Vision.module.css';

const EVAL_TONE = { RUNNING: 'warning', DONE: 'success', FAILED: 'danger' } as const;

function StartEval() {
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
      <h2 id="eval-title" className={styles.sectionTitle}>Đo engine đang nạp</h2>
      <p className={styles.note}>Chạy đúng engine ANPR đang nạp trên AI host với ảnh cắt trong console. Chỉ đo trên golden đã khoá.</p>
      {snapshots.error && <ErrorBlock error={snapshots.error} />}
      <div className={styles.formGrid}>
        <SelectField label="Golden đã khoá" required value={snapshotId} onChange={(e) => setSnapshotId(e.target.value)}>
          <option value="">{frozen.length ? 'Chọn golden' : 'Chưa có golden đã khoá'}</option>
          {frozen.map((s) => <option key={s.id} value={s.id}>{s.name} · {fmtInt(s.sample_count)} mẫu</option>)}
        </SelectField>
        <Button type="submit" disabled={!snapshotId} loading={start.isPending}>Bắt đầu đo</Button>
      </div>
      {start.error && <ErrorBlock error={start.error} />}
    </form>
  );
}

function RegisterModel() {
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
      <h2 id="register-title" className={styles.sectionTitle}>Đăng ký phiên bản model</h2>
      <div className={styles.formGrid}>
        <TextField label="Tên" required value={form.name} onChange={set('name')} />
        <TextField label="Phiên bản" required maxLength={64} value={form.version} onChange={set('version')} />
        <TextField label="artifact_key" hint="models/<tên>/<phiên bản>/…" required value={form.artifact_key} onChange={set('artifact_key')} />
        <TextField label="sha256 weights" required minLength={64} maxLength={64} value={form.sha256} onChange={set('sha256')} />
        <TextField label="Ghi chú" maxLength={500} value={form.note} onChange={set('note')} />
        <Button type="submit" loading={register.isPending}>Đăng ký</Button>
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
        title="Model & lượt đo"
        description="Đề xuất cần một lượt đo xong trên golden đã khoá với đúng weights của model. Promote cần AI Lead khác người đề xuất và xác thực lại."
      />
      {canEvaluate && <section className={styles.section}><StartEval /></section>}
      <section className={styles.section} aria-labelledby="evals-title">
        <h2 id="evals-title" className={styles.sectionTitle}>Lượt đo</h2>
        {evals.isPending && <Loading />}
        {evals.error && <ErrorBlock error={evals.error} onRetry={() => void evals.refetch()} />}
        {evals.data?.length === 0 && <EmptyState title="Chưa có lượt đo nào" />}
        {evals.data && evals.data.length > 0 && (
          <div className={table.wrap}>
            <table className={table.table}>
              <thead>
                <tr>
                  <th scope="col">Bắt đầu</th>
                  <th scope="col">Golden</th>
                  <th scope="col">Trạng thái</th>
                  <th scope="col">Engine</th>
                  <th scope="col" className={table.num}>Mẫu</th>
                  <th scope="col" className={table.num}>Đúng (bỏ dấu)</th>
                  <th scope="col" className={table.num}>Đúng tuyệt đối</th>
                  <th scope="col" className={table.num}>CER TB</th>
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
        <h2 id="models-title" className={styles.sectionTitle}>Phiên bản model</h2>
        {models.isPending && <Loading />}
        {models.error && <ErrorBlock error={models.error} onRetry={() => void models.refetch()} />}
        {models.data?.length === 0 && <EmptyState icon={<Boxes size={28} />} title="Chưa đăng ký model nào" />}
        {models.data && models.data.length > 0 && (
          <div className={table.wrap}>
            <table className={table.table}>
              <thead>
                <tr>
                  <th scope="col">Model</th>
                  <th scope="col">Trạng thái</th>
                  <th scope="col">sha256</th>
                  <th scope="col">Đề xuất / duyệt</th>
                  <th scope="col">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {models.data.map((m) => (
                  <tr key={m.id}>
                    <td>
                      <div>{m.name}@{m.version}</div>
                      <div className={table.mono}>{m.artifact_key}</div>
                    </td>
                    <td><Badge tone={STAGE_TONE[m.stage]}>{STAGE_LABEL[m.stage]}</Badge></td>
                    <td className={table.mono} title={m.sha256}>{m.sha256.slice(0, 12)}</td>
                    <td className={table.muted}>
                      {m.proposed_by ? `${m.proposed_by} · ${fmtDateTime(m.proposed_at!)}` : DASH}
                      {m.approved_by && <div>Duyệt: {m.approved_by} · {fmtDateTime(m.approved_at!)}</div>}
                    </td>
                    <td>
                      {m.stage === 'candidate' && canPropose && (
                        <ReasonAction label="Đề xuất" onSubmit={(reason) => propose.mutateAsync({ id: m.id, reason })} />
                      )}
                      {m.stage === 'proposed' && canPromote && (
                        <ReasonAction
                          label="Đưa lên production"
                          variant="accent"
                          disabled={m.proposed_by_id === me.data?.member_id}
                          disabledHint="Bạn đề xuất model này — cần AI Lead khác."
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
