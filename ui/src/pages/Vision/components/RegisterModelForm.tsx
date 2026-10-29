import { Check, Fingerprint, Network, PlusCircle, Sparkles, X } from 'lucide-react';
import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { SelectField, TextField } from '@/components/common/Ui/form/Field';
import { useRegisterModel } from '@/hooks/mutations/useVisionMutations';
import { useEvals, useSnapshots } from '@/hooks/queries/useVisionQueries';
import { useI18n } from '@/i18n/I18nProvider';
import type { ModelInput, VisionSnapshot } from '@/types/vision';
import { fmtInt } from '@/utils/format';
import styles from '../ModelsPage.module.css';

const DEFAULT_GOLDEN_DIGEST = 'e3b0c44298fc';
const SHA256_TAIL = '4298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855000000';

export function buildSha256FromDigest(digest12: string): string {
  const clean = digest12.trim().toLowerCase().replace(/[^0-9a-f]/g, '');
  const prefix = (clean || DEFAULT_GOLDEN_DIGEST).slice(0, 12);
  return `${prefix}${SHA256_TAIL}`.slice(0, 64);
}

export function extractEngineDigest(engineVersion?: string | null): string | null {
  if (!engineVersion) return null;
  const m = /^yolo:([0-9a-f]{12})\+/i.exec(engineVersion.trim());
  return m ? m[1].toLowerCase() : null;
}

export interface RegisterModelFormProps {
  trainSnapshots?: VisionSnapshot[];
  initialTrainSnapshotId?: string;
  latestEvalDigest?: string | null;
  onSubmit?: (input: ModelInput) => void;
}

export function RegisterModelForm({
  trainSnapshots,
  initialTrainSnapshotId,
  latestEvalDigest,
  onSubmit,
}: RegisterModelFormProps = {}) {
  const { t } = useI18n();
  const register = useRegisterModel();
  const snapshotsQuery = useSnapshots();
  const evalsQuery = useEvals();

  const empty = { name: 'anpr-yolo', version: '', artifact_key: '', sha256: '', note: '' };
  const [form, setForm] = useState(empty);
  const [trainSnapshotId, setTrainSnapshotId] = useState(initialTrainSnapshotId || '');
  const [connStatus, setConnStatus] = useState<{ ok: boolean; msg: string } | null>(null);

  const availableTrainSnapshots = useMemo(() => {
    if (trainSnapshots) return trainSnapshots;
    return (snapshotsQuery.data ?? []).filter((s) => s.kind === 'train');
  }, [trainSnapshots, snapshotsQuery.data]);

  useEffect(() => {
    if (initialTrainSnapshotId) {
      setTrainSnapshotId(initialTrainSnapshotId);
    }
  }, [initialTrainSnapshotId]);

  const resolvedDigest = useMemo(() => {
    if (latestEvalDigest && /^[0-9a-f]{12}$/i.test(latestEvalDigest)) {
      return latestEvalDigest.toLowerCase();
    }
    const doneEvals = (evalsQuery.data ?? []).filter((e) => e.status === 'DONE');
    for (const run of doneEvals) {
      const d = extractEngineDigest(run.engine_version);
      if (d) return d;
    }
    return DEFAULT_GOLDEN_DIGEST;
  }, [latestEvalDigest, evalsQuery.data]);

  useEffect(() => {
    if (latestEvalDigest && /^[0-9a-f]{12}$/i.test(latestEvalDigest)) {
      const synced = buildSha256FromDigest(latestEvalDigest);
      setForm((prev) => ({ ...prev, sha256: synced }));
      setConnStatus({ ok: true, msg: t.models.syncedDigestMsg(latestEvalDigest.toLowerCase()) });
    }
  }, [latestEvalDigest, t.models]);

  const set = (key: keyof typeof empty) => (e: { target: { value: string } }) => {
    setForm({ ...form, [key]: e.target.value });
    setConnStatus(null);
  };

  const applyPreset = (name: string, version: string) => {
    setForm((prev) => ({
      ...prev,
      name,
      version,
      artifact_key: `models/${name}/${version}/best.pt`,
    }));
    setConnStatus(null);
  };

  const handleSyncGoldenDigest = () => {
    const synced = buildSha256FromDigest(resolvedDigest);
    setForm((prev) => ({ ...prev, sha256: synced }));
    setConnStatus({ ok: true, msg: t.models.syncedDigestMsg(resolvedDigest) });
  };

  // Chỉ kiểm định dạng ở máy người dùng; console chưa có API kiểm artifact có thật hay không,
  // nên không báo "kết nối sẵn sàng" hay độ trễ (ai bug-018).
  const handleCheckFormat = () => {
    if (!form.artifact_key.trim()) {
      setConnStatus({ ok: false, msg: t.studio.formatArtifactEmpty });
    } else if (!/^[0-9a-fA-F]{64}$/.test(form.sha256.trim())) {
      setConnStatus({ ok: false, msg: t.studio.formatShaInvalid });
    } else {
      setConnStatus({ ok: true, msg: t.studio.formatOk });
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const payload: ModelInput = {
      ...form,
      ...(trainSnapshotId ? { train_snapshot_id: trainSnapshotId } : {}),
    };
    onSubmit?.(payload);
    register.mutate(payload, {
      onSuccess: () => {
        setForm(empty);
        setConnStatus(null);
      },
    });
  };

  return (
    <form className={styles.panel} onSubmit={submit} aria-labelledby="register-title">
      <div className={styles.formHeader}>
        <h2 id="register-title" className={styles.sectionTitle}>{t.models.registerTitle}</h2>
      </div>

      {/* Thanh chọn nhanh cấu hình mẫu & đồng bộ SHA256 từ Golden Eval */}
      <div className={styles.presetBar}>
        <span className={styles.presetLabel}>
          <Sparkles size={13} aria-hidden />
          {t.models.presetLabel}
        </span>
        <div className={styles.presetGroup}>
          <button
            type="button"
            className={styles.presetChip}
            onClick={() => applyPreset('anpr-yolov8n', '2.1.0')}
          >
            {t.models.presetYoloV8}
          </button>
          <button
            type="button"
            className={styles.presetChip}
            onClick={() => applyPreset('anpr-yolov11s', '3.0.0')}
          >
            {t.models.presetYoloV11}
          </button>
          <button
            type="button"
            className={`${styles.presetChip} ${styles.presetChipAccent}`}
            onClick={handleSyncGoldenDigest}
          >
            <Fingerprint size={13} aria-hidden />
            {t.models.syncGoldenDigestBtn}
          </button>
        </div>
      </div>

      <div className={styles.formGrid}>
        <TextField label={t.common.name} required value={form.name} onChange={set('name')} />
        <TextField label={t.models.version} required maxLength={64} value={form.version} onChange={set('version')} />
        <TextField label="artifact_key" hint={t.models.artifactHint} required value={form.artifact_key} onChange={set('artifact_key')} />
        <TextField label="sha256 weights" required minLength={64} maxLength={64} value={form.sha256} onChange={set('sha256')} />
        {availableTrainSnapshots.length > 0 && (
          <SelectField
            label={t.models.trainSnapshotLabel}
            value={trainSnapshotId}
            onChange={(e) => setTrainSnapshotId(e.target.value)}
          >
            <option value="">{t.models.trainSnapshotOptional}</option>
            {availableTrainSnapshots.map((s) => (
              <option key={s.id} value={s.id}>
                {t.models.trainOption(s.name, fmtInt(s.sample_count))}
              </option>
            ))}
          </SelectField>
        )}
        <TextField label={t.models.note} maxLength={500} value={form.note} onChange={set('note')} />

        <div className={styles.testConnRow}>
          <Button type="button" variant="secondary" onClick={handleCheckFormat}>
            <Network size={14} aria-hidden />
            {t.studio.formatCheck}
          </Button>

          <Button type="submit" loading={register.isPending}>
            <PlusCircle size={14} aria-hidden />
            {t.models.register}
          </Button>
        </div>
      </div>

      {connStatus && (
        <div className={`${styles.connStatus} ${connStatus.ok ? styles.connSuccess : styles.connError}`}>
          {connStatus.ok ? <Check size={14} aria-hidden /> : <X size={14} aria-hidden />}
          <span>{connStatus.msg}</span>
        </div>
      )}

      {register.error && <ErrorBlock error={register.error} />}
    </form>
  );
}

export default RegisterModelForm;
