import { Sparkles } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { SelectField, TextField } from '@/components/common/Ui/form/Field';
import { useCreateSnapshot } from '@/hooks/mutations/useVisionMutations';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtInt } from '@/utils/format';
import styles from '../DatasetsPage.module.css';

function todayStamp(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}${m}${d}`;
}

export function CreateSnapshotForm() {
  const { t } = useI18n();
  const create = useCreateSnapshot();
  const [kind, setKind] = useState<'train' | 'golden'>('train');
  const [name, setName] = useState('');

  const stamp = todayStamp();

  const applyTemplate = (targetKind: 'train' | 'golden', prefix: string) => {
    setKind(targetKind);
    setName(`${prefix}-${stamp}`);
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    create.mutate({ kind, name: name.trim() }, { onSuccess: () => setName('') });
  };

  return (
    <form className={styles.panel} onSubmit={submit} aria-labelledby="snapshot-title">
      <h2 id="snapshot-title" className={styles.sectionTitle}>{t.datasets.createTitle}</h2>
      <p className={styles.note}>{t.datasets.createNote}</p>

      <div className={styles.templateBar}>
        <span className={styles.templateLabel}>
          <Sparkles size={13} aria-hidden />
          {t.datasets.templateLabel}
        </span>
        <div className={styles.templateGroup}>
          <button
            type="button"
            className={`${styles.templateChip} ${kind === 'train' && name.startsWith('train-anpr-') ? styles.templateChipActive : ''}`}
            onClick={() => applyTemplate('train', 'train-anpr')}
          >
            {t.datasets.tplTrainAnpr}
          </button>
          <button
            type="button"
            className={`${styles.templateChip} ${kind === 'train' && name.startsWith('train-night-') ? styles.templateChipActive : ''}`}
            onClick={() => applyTemplate('train', 'train-night')}
          >
            {t.datasets.tplTrainNight}
          </button>
          <button
            type="button"
            className={`${styles.templateChip} ${kind === 'golden' && name.startsWith('golden-benchmark-') ? styles.templateChipActive : ''}`}
            onClick={() => applyTemplate('golden', 'golden-benchmark')}
          >
            {t.datasets.tplGoldenBench}
          </button>
          <button
            type="button"
            className={`${styles.templateChip} ${kind === 'golden' && name.startsWith('golden-gate-audit-') ? styles.templateChipActive : ''}`}
            onClick={() => applyTemplate('golden', 'golden-gate-audit')}
          >
            {t.datasets.tplGoldenGate}
          </button>
        </div>
      </div>

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
