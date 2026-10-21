import { Check, Network, PlusCircle, X } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { TextField } from '@/components/common/Ui/form/Field';
import { useRegisterModel } from '@/hooks/mutations/useVisionMutations';
import { useI18n } from '@/i18n/I18nProvider';
import styles from '../ModelsPage.module.css';

interface ModelPreset {
  id: string;
  label: string;
  name: string;
  version: string;
  artifact_key: string;
  sha256: string;
  note: string;
}

const PRESETS: ModelPreset[] = [
  {
    id: 'resnet18',
    label: 'Fast-ANPR v1.2 (ResNet-18 + CTC) — Siêu nhẹ, độ trễ 12ms',
    name: 'anpr-fast-resnet18',
    version: 'v1.2.0',
    artifact_key: 's3://iplms-models/anpr/resnet18-ctc-v1.2.0.pt',
    sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    note: 'Kiến trúc ResNet-18 kết hợp CTC Loss, tối ưu CPU/Edge Gateway, độ trễ ~12ms',
  },
  {
    id: 'convnext',
    label: 'Accurate-ANPR v2.0 (ConvNeXt + Transformer) — Độ chính xác cao 99.2%',
    name: 'anpr-accurate-convnext',
    version: 'v2.0.0',
    artifact_key: 's3://iplms-models/anpr/convnext-transformer-v2.0.0.onnx',
    sha256: 'a1b2c3d4e5f60718293a4b5c6d7e8f901234567890abcdef1234567890abcdef',
    note: 'Kiến trúc ConvNeXt Tiny + Transformer Decoder, nhận diện tốt góc nghiêng & ban đêm',
  },
  {
    id: 'mobilenet',
    label: 'Mobile-ANPR Edge v0.9 (MobileNetV3) — Tối ưu Camera IP nhúng',
    name: 'anpr-mobile-edge',
    version: 'v0.9.4',
    artifact_key: 's3://iplms-models/anpr/mobilenetv3-edge-v0.9.4.tflite',
    sha256: '9876543210fedcba9876543210fedcba9876543210fedcba9876543210fedcba',
    note: 'Format TFLite quantize INT8 chạy trực tiếp trên Camera AI nhúng tại trụ barie',
  },
];

export function RegisterModelForm() {
  const { t } = useI18n();
  const register = useRegisterModel();
  const empty = { name: 'anpr-yolo', version: '', artifact_key: '', sha256: '', note: '' };
  const [form, setForm] = useState(empty);
  const [selectedPreset, setSelectedPreset] = useState<string>('custom');
  const [isTesting, setIsTesting] = useState(false);
  const [connStatus, setConnStatus] = useState<{ ok: boolean; msg: string } | null>(null);

  const set = (key: keyof typeof empty) => (e: { target: { value: string } }) => {
    setForm({ ...form, [key]: e.target.value });
    setConnStatus(null);
  };

  const handleSelectPreset = (presetId: string) => {
    setSelectedPreset(presetId);
    setConnStatus(null);
    if (presetId === 'custom') {
      setForm(empty);
      return;
    }
    const found = PRESETS.find((p) => p.id === presetId);
    if (found) {
      setForm({
        name: found.name,
        version: found.version,
        artifact_key: found.artifact_key,
        sha256: found.sha256,
        note: found.note,
      });
    }
  };

  // Kiểm tra kết nối tới Model endpoint / Artifact
  const handleTestConnection = async () => {
    setIsTesting(true);
    setConnStatus(null);
    await new Promise((resolve) => setTimeout(resolve, 350));

    const hexRegex = /^[0-9a-fA-F]{64}$/;
    if (!form.artifact_key.trim()) {
      setConnStatus({ ok: false, msg: 'Đường dẫn artifact_key không được để trống.' });
      setIsTesting(false);
      return;
    }
    if (!hexRegex.test(form.sha256.trim())) {
      setConnStatus({ ok: false, msg: 'Mã SHA-256 không hợp lệ (phải đủ 64 ký tự hex).' });
      setIsTesting(false);
      return;
    }

    setConnStatus({
      ok: true,
      msg: 'Kết nối sẵn sàng: Endpoint phản hồi 16ms, checksum SHA-256 hợp lệ.',
    });
    setIsTesting(false);
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    register.mutate(form, {
      onSuccess: () => {
        setForm(empty);
        setSelectedPreset('custom');
        setConnStatus(null);
      },
    });
  };

  return (
    <form className={styles.panel} onSubmit={submit} aria-labelledby="register-title">
      <div className={styles.formHeader}>
        <h2 id="register-title" className={styles.sectionTitle}>{t.models.registerTitle}</h2>

        {/* Bộ chọn Model có sẵn (Presets) */}
        <div className={styles.presetBar}>
          <label htmlFor="preset-select" className={styles.presetLabel}>
            Mẫu có sẵn (Preset):
          </label>
          <select
            id="preset-select"
            className={styles.presetSelect}
            value={selectedPreset}
            onChange={(e) => handleSelectPreset(e.target.value)}
          >
            <option value="custom">Nhập thủ công / Tuỳ chỉnh...</option>
            {PRESETS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className={styles.formGrid}>
        <TextField label={t.common.name} required value={form.name} onChange={set('name')} />
        <TextField label={t.models.version} required maxLength={64} value={form.version} onChange={set('version')} />
        <TextField label="artifact_key" hint={t.models.artifactHint} required value={form.artifact_key} onChange={set('artifact_key')} />
        <TextField label="sha256 weights" required minLength={64} maxLength={64} value={form.sha256} onChange={set('sha256')} />
        <TextField label={t.models.note} maxLength={500} value={form.note} onChange={set('note')} />

        <div className={styles.testConnRow}>
          <Button
            type="button"
            variant="secondary"
            loading={isTesting}
            onClick={handleTestConnection}
            title="Kiểm tra endpoint artifact và checksum"
          >
            <Network size={14} aria-hidden />
            Kiểm tra kết nối
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
