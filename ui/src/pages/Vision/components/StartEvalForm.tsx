import { useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { SelectField } from '@/components/common/Ui/form/Field';
import { useStartEval } from '@/hooks/mutations/useVisionMutations';
import { useSnapshots } from '@/hooks/queries/useVisionQueries';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtInt } from '@/utils/format';
import styles from '../ModelsPage.module.css';

export function StartEvalForm() {
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

export default StartEvalForm;
