import { Cpu, Play } from 'lucide-react';
import { useEffect, useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { SelectField } from '@/components/common/Ui/form/Field';
import { useStartEval } from '@/hooks/mutations/useVisionMutations';
import { useSnapshots } from '@/hooks/queries/useVisionQueries';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtInt } from '@/utils/format';
import styles from '../ModelsPage.module.css';

const ENGINE_PRESETS = [
  { label: 'yolo:e3b0c44298fc+easyocr:1.7', digest: 'e3b0c44298fc' },
  { label: 'yolo:a1b2c3d4e5f6+paddleocr:2.7', digest: 'a1b2c3d4e5f6' },
] as const;

export interface StartEvalFormProps {
  initialSnapshotId?: string;
  onSelectEngineDigest?: (digest: string) => void;
}

export function StartEvalForm({ initialSnapshotId, onSelectEngineDigest }: StartEvalFormProps = {}) {
  const { t } = useI18n();
  const snapshots = useSnapshots();
  const start = useStartEval();
  const [snapshotId, setSnapshotId] = useState(initialSnapshotId || '');
  const [selectedEngine, setSelectedEngine] = useState<string>(ENGINE_PRESETS[0].label);
  const frozen = snapshots.data?.filter((s) => s.kind === 'golden' && s.frozen_at) ?? [];

  useEffect(() => {
    if (initialSnapshotId && frozen.some((s) => s.id === initialSnapshotId)) {
      setSnapshotId(initialSnapshotId);
    } else if (!snapshotId && frozen.length > 0) {
      setSnapshotId(frozen[0].id);
    }
  }, [initialSnapshotId, frozen, snapshotId]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    start.mutate(snapshotId);
  };

  return (
    <form className={styles.panel} onSubmit={submit} aria-labelledby="eval-title">
      <div className={styles.formHeader}>
        <div>
          <h2 id="eval-title" className={styles.sectionTitle}>{t.models.evalTitle}</h2>
          <p className={styles.note}>{t.models.evalNote}</p>
        </div>
      </div>

      <div className={styles.presetBar}>
        <span className={styles.presetLabel}>
          <Cpu size={13} aria-hidden />
          {t.models.enginePresetsLabel}
        </span>
        <div className={styles.presetGroup}>
          {ENGINE_PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              className={`${styles.presetChip} ${selectedEngine === preset.label ? styles.presetChipActive : ''}`}
              onClick={() => {
                setSelectedEngine(preset.label);
                onSelectEngineDigest?.(preset.digest);
              }}
            >
              <code>{preset.label}</code>
            </button>
          ))}
        </div>
      </div>

      {snapshots.error && <ErrorBlock error={snapshots.error} />}
      <div className={styles.formGrid}>
        <SelectField
          label={t.models.frozenGolden}
          required
          value={snapshotId}
          onChange={(e) => setSnapshotId(e.target.value)}
        >
          <option value="">{frozen.length ? t.models.pickGolden : t.models.noGolden}</option>
          {frozen.map((s) => (
            <option key={s.id} value={s.id}>
              {t.models.goldenOption(s.name, fmtInt(s.sample_count))}
            </option>
          ))}
        </SelectField>
        <Button type="submit" disabled={!snapshotId} loading={start.isPending}>
          <Play size={14} aria-hidden />
          {t.models.startEval}
        </Button>
      </div>
      {start.error && <ErrorBlock error={start.error} />}
    </form>
  );
}

export default StartEvalForm;
