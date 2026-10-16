import { Database, Lock } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import table from '@/components/common/Ui/data-display/Table.module.css';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { SelectField, TextField } from '@/components/common/Ui/form/Field';
import { ReasonAction } from '@/components/common/Ui/form/ReasonAction';
import { PageHeader } from '@/components/layout/PageHeader';
import { useCan } from '@/hooks/useConsole';
import { useCreateSnapshot, useFreezeSnapshot, useSnapshots } from '@/hooks/useVision';
import { fmtDateTime, fmtInt } from '@/utils/format';
import styles from './Vision.module.css';

function CreateSnapshot() {
  const create = useCreateSnapshot();
  const [kind, setKind] = useState<'train' | 'golden'>('train');
  const [name, setName] = useState('');

  const submit = (event: FormEvent) => {
    event.preventDefault();
    create.mutate({ kind, name: name.trim() }, { onSuccess: () => setName('') });
  };

  return (
    <form className={styles.panel} onSubmit={submit} aria-labelledby="snapshot-title">
      <h2 id="snapshot-title" className={styles.sectionTitle}>Tạo snapshot</h2>
      <p className={styles.note}>
        Lấy mọi nhãn đã duyệt (bỏ ảnh hỏng). Train tự loại các nhóm ảnh đã nằm trong golden đã khoá để không rò giữa train và test; train/val chia theo nhóm, cố định giữa các lần tạo.
      </p>
      <div className={styles.formGrid}>
        <SelectField label="Loại" value={kind} onChange={(e) => setKind(e.target.value as 'train' | 'golden')}>
          <option value="train">train (train + val)</option>
          <option value="golden">golden (test-golden)</option>
        </SelectField>
        <TextField label="Tên" required minLength={3} maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />
        <Button type="submit" loading={create.isPending}>Tạo</Button>
      </div>
      {create.error && <ErrorBlock error={create.error} />}
      {create.data && <p className={styles.note} role="status">Đã tạo snapshot {fmtInt(create.data.sample_count)} mẫu.</p>}
    </form>
  );
}

export function DatasetsPage() {
  const snapshots = useSnapshots();
  const freeze = useFreezeSnapshot();
  const canCreate = useCan('ai:dataset:snapshot');
  const canFreeze = useCan('ai:golden:freeze');

  return (
    <>
      <PageHeader
        title="Dataset & golden"
        description="Snapshot là manifest khoá bằng sha256 của danh sách mẫu. Golden phải khoá (AI Lead, xác thực lại) trước khi dùng làm thước đo model."
      />
      {canCreate && <section className={styles.section}><CreateSnapshot /></section>}
      <section className={styles.section} aria-labelledby="snapshots-title">
        <h2 id="snapshots-title" className={styles.sectionTitle}>Snapshot</h2>
        {snapshots.isPending && <Loading />}
        {snapshots.error && <ErrorBlock error={snapshots.error} onRetry={() => void snapshots.refetch()} />}
        {snapshots.data?.length === 0 && <EmptyState icon={<Database size={28} />} title="Chưa có snapshot" description="Cần nhãn đã duyệt trước khi tạo snapshot." />}
        {snapshots.data && snapshots.data.length > 0 && (
          <div className={table.wrap}>
            <table className={table.table}>
              <thead>
                <tr>
                  <th scope="col">Tên</th>
                  <th scope="col">Loại</th>
                  <th scope="col" className={table.num}>Mẫu</th>
                  <th scope="col">sha256</th>
                  <th scope="col">Tạo</th>
                  <th scope="col">Khoá</th>
                </tr>
              </thead>
              <tbody>
                {snapshots.data.map((s) => (
                  <tr key={s.id}>
                    <td>{s.name}</td>
                    <td><Badge tone={s.kind === 'golden' ? 'accent' : 'neutral'}>{s.kind}</Badge></td>
                    <td className={table.num}>{fmtInt(s.sample_count)}</td>
                    <td className={table.mono} title={s.samples_sha256}>{s.samples_sha256.slice(0, 12)}</td>
                    <td className={table.muted}>{s.created_by} · {fmtDateTime(s.created_at)}</td>
                    <td>
                      {s.frozen_at ? (
                        <span className={table.muted}><Lock size={12} aria-hidden /> {s.frozen_by} · {fmtDateTime(s.frozen_at)}</span>
                      ) : s.kind === 'golden' && canFreeze ? (
                        <ReasonAction label="Khoá golden" onSubmit={(reason) => freeze.mutateAsync({ id: s.id, reason })} />
                      ) : (
                        <span className={table.muted}>—</span>
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
