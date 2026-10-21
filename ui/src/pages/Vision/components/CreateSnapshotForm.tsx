import { useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { SelectField, TextField } from '@/components/common/Ui/form/Field';
import { useCreateSnapshot } from '@/hooks/mutations/useVisionMutations';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtInt } from '@/utils/format';
import styles from '../DatasetsPage.module.css';

export function CreateSnapshotForm() {
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
      <p className={styles.note}>{t.datasets.createNote}</p>
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

export default CreateSnapshotForm;
