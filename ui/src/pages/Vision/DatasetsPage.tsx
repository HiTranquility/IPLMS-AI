import { Database, Lock } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import table from '@/components/common/Ui/data-display/table.module.css';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { SelectField, TextField } from '@/components/common/Ui/form/Field';
import { ReasonAction } from '@/components/common/Ui/form/ReasonAction';
import { PageHeader } from '@/components/layout/PageHeader';
import { useCan } from '@/hooks/useConsole';
import { useCreateSnapshot, useFreezeSnapshot, useSnapshots } from '@/hooks/useVision';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtDateTime, fmtInt } from '@/utils/format';
import styles from './vision.module.css';

function CreateSnapshot() {
  const { t } = useI18n();
  const create = useCreateSnapshot();
  const [kind, setKind] = useState<'train' | 'golden'>('train');
  const [name, setName] = useState('');

  const submit = (event: FormEvent) => {
    event.preventDefault();
    create.mutate({ kind, name: name.trim() }, { onSuccess: () => setName('') });
  };

  return (
    <form className={styles.panel} onSubmit={submit} aria-labelledby="snapshot-title">
      <h2 id="snapshot-title" className={styles.sectionTitle}>{t.datasets.createTitle}</h2>
      <p className={styles.note}>
        {t.datasets.createNote}
      </p>
      <div className={styles.formGrid}>
        <SelectField label={t.datasets.kind} value={kind} onChange={(e) => setKind(e.target.value as 'train' | 'golden')}>
          <option value="train">train (train + val)</option>
          <option value="golden">golden (test-golden)</option>
        </SelectField>
        <TextField label={t.common.name} required minLength={3} maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />
        <Button type="submit" loading={create.isPending}>{t.datasets.create}</Button>
      </div>
      {create.error && <ErrorBlock error={create.error} />}
      {create.data && <p className={styles.note} role="status">{t.datasets.created(fmtInt(create.data.sample_count))}</p>}
    </form>
  );
}

export function DatasetsPage() {
  const { t } = useI18n();
  const snapshots = useSnapshots();
  const freeze = useFreezeSnapshot();
  const canCreate = useCan('ai:dataset:snapshot');
  const canFreeze = useCan('ai:golden:freeze');

  return (
    <>
      <PageHeader
        title={t.datasets.title}
        description={t.datasets.desc}
      />
      {canCreate && <section className={styles.section}><CreateSnapshot /></section>}
      <section className={styles.section} aria-labelledby="snapshots-title">
        <h2 id="snapshots-title" className={styles.sectionTitle}>{t.datasets.listTitle}</h2>
        {snapshots.isPending && <Loading />}
        {snapshots.error && <ErrorBlock error={snapshots.error} onRetry={() => void snapshots.refetch()} />}
        {snapshots.data?.length === 0 && <EmptyState icon={<Database size={28} />} title={t.datasets.emptyTitle} description={t.datasets.emptyDesc} />}
        {snapshots.data && snapshots.data.length > 0 && (
          <div className={table.wrap}>
            <table className={table.table}>
              <thead>
                <tr>
                  <th scope="col">{t.common.name}</th>
                  <th scope="col">{t.datasets.kind}</th>
                  <th scope="col" className={table.num}>{t.common.sample}</th>
                  <th scope="col">sha256</th>
                  <th scope="col">{t.datasets.createdCol}</th>
                  <th scope="col">{t.datasets.frozenCol}</th>
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
                        <ReasonAction label={t.datasets.freeze} onSubmit={(reason) => freeze.mutateAsync({ id: s.id, reason })} />
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
