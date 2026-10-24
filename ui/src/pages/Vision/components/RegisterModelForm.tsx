import { Check, Network, PlusCircle, X } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { TextField } from '@/components/common/Ui/form/Field';
import { useRegisterModel } from '@/hooks/mutations/useVisionMutations';
import { useI18n } from '@/i18n/I18nProvider';
import styles from '../ModelsPage.module.css';

export function RegisterModelForm() {
  const { t } = useI18n();
  const register = useRegisterModel();
  const empty = { name: 'anpr-yolo', version: '', artifact_key: '', sha256: '', note: '' };
  const [form, setForm] = useState(empty);
  const [connStatus, setConnStatus] = useState<{ ok: boolean; msg: string } | null>(null);

  const set = (key: keyof typeof empty) => (e: { target: { value: string } }) => {
    setForm({ ...form, [key]: e.target.value });
    setConnStatus(null);
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
    register.mutate(form, {
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

      <div className={styles.formGrid}>
        <TextField label={t.common.name} required value={form.name} onChange={set('name')} />
        <TextField label={t.models.version} required maxLength={64} value={form.version} onChange={set('version')} />
        <TextField label="artifact_key" hint={t.models.artifactHint} required value={form.artifact_key} onChange={set('artifact_key')} />
        <TextField label="sha256 weights" required minLength={64} maxLength={64} value={form.sha256} onChange={set('sha256')} />
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
