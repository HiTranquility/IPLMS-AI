import { useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { TextField } from '@/components/common/Ui/form/Field';
import { useProposePolicy } from '@/hooks/mutations/useVisionMutations';
import { useI18n } from '@/i18n/I18nProvider';
import styles from '../VisionOverviewPage.module.css';

export interface ProposePolicyFormProps {
  suggested: number | null;
}

export function ProposePolicyForm({ suggested }: ProposePolicyFormProps) {
  const { t } = useI18n();
  const propose = useProposePolicy();
  const [threshold, setThreshold] = useState(String(suggested ?? 0.9));
  const [auditRate, setAuditRate] = useState('3');
  const [reason, setReason] = useState('');

  const submit = (event: FormEvent) => {
    event.preventDefault();
    propose.mutate(
      { threshold: Number(threshold), auditRate: Number(auditRate) / 100, reason: reason.trim() },
      { onSuccess: () => setReason('') },
    );
  };

  return (
    <form className={styles.panel} onSubmit={submit} aria-labelledby="propose-title">
      <h2 id="propose-title" className={styles.sectionTitle}>{t.visionOverview.proposeTitle}</h2>
      <div className={styles.formGrid}>
        <TextField label={t.visionOverview.thresholdField} type="number" min={0.5} max={0.99} step={0.01} required value={threshold} onChange={(e) => setThreshold(e.target.value)} />
        <TextField label={t.visionOverview.auditRateField} type="number" min={1} max={50} step={0.5} required value={auditRate} onChange={(e) => setAuditRate(e.target.value)} />
        <TextField label={t.common.reason} required minLength={3} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
        <Button type="submit" loading={propose.isPending}>{t.common.propose}</Button>
      </div>
      <p className={styles.note}>{t.visionOverview.proposeNote}</p>
      {propose.error && <ErrorBlock error={propose.error} />}
    </form>
  );
}

export default ProposePolicyForm;
