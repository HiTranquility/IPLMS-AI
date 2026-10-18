import { Tags } from 'lucide-react';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import type { LabelVerdict, VisionSample } from '@/api/types';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { TextField } from '@/components/common/Ui/form/Field';
import { CropImage } from '@/components/common/Ui/media/CropImage';
import { PageHeader } from '@/components/layout/PageHeader';
import { useAddLabel, useLabelQueue } from '@/hooks/useVision';
import { useI18n } from '@/i18n/I18nProvider';
import { DASH, fmtPercent } from '@/utils/format';
import styles from './vision.module.css';

function LabelForm({ sample, remaining }: { sample: VisionSample; remaining: number }) {
  const { t } = useI18n();
  const add = useAddLabel();
  const [correcting, setCorrecting] = useState(false);
  const [plate, setPlate] = useState('');
  const plateRef = useRef<HTMLInputElement>(null);

  const send = (verdict: LabelVerdict) => add.mutate({ captureId: sample.capture_id, verdict, plateText: verdict === 'CORRECTED' ? plate : '' });

  // Phím tắt giống trang gán nhãn của moderator (platform): 1 đúng · 2 sửa · 3 hỏng.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (add.isPending || target?.closest('input, textarea, select')) return;
      if (event.key === '1') send('CORRECT');
      if (event.key === '2') setCorrecting(true);
      if (event.key === '3') send('UNUSABLE');
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  useEffect(() => {
    if (correcting) plateRef.current?.focus();
  }, [correcting]);

  const submitCorrection = (event: FormEvent) => {
    event.preventDefault();
    send('CORRECTED');
  };

  return (
    <section className={styles.labelCard} aria-label={t.label.card}>
      <CropImage captureId={sample.capture_id} size="lg" />
      <dl className={styles.facts}>
        <dt>{t.label.gatePlate}</dt><dd className={styles.plate}>{sample.confirmed_plate || DASH}</dd>
        <dt>{t.label.machine}</dt><dd className={styles.mono}>{sample.machine_plate || DASH} · {fmtPercent(sample.machine_confidence)}</dd>
        <dt>{t.label.why}</dt>
        <dd className={styles.badges}>
          {sample.human_corrected && <Badge tone="accent">{t.label.staffCorrected}</Badge>}
          {sample.selection_reasons.map((r) => <Badge key={r}>{t.vision.reason[r] ?? r}</Badge>)}
        </dd>
      </dl>
      <p className={styles.question}>{t.label.question}</p>
      <div className={styles.actions}>
        <Button onClick={() => send('CORRECT')} loading={add.isPending && add.variables?.verdict === 'CORRECT'}>
          {t.label.correct} <kbd className={styles.kbd}>1</kbd>
        </Button>
        <Button variant="secondary" onClick={() => setCorrecting(true)}>
          {t.label.fix} <kbd className={styles.kbd}>2</kbd>
        </Button>
        <Button variant="secondary" onClick={() => send('UNUSABLE')} loading={add.isPending && add.variables?.verdict === 'UNUSABLE'}>
          {t.label.unusable} <kbd className={styles.kbd}>3</kbd>
        </Button>
      </div>
      {correcting && (
        <form className={styles.inline} onSubmit={submitCorrection}>
          <TextField ref={plateRef} label={t.label.rightPlate} required minLength={4} maxLength={20} value={plate} onChange={(e) => setPlate(e.target.value.toUpperCase())} />
          <Button type="submit" variant="accent" loading={add.isPending}>{t.label.saveFix}</Button>
        </form>
      )}
      {add.error && <ErrorBlock error={add.error} />}
      <p className={styles.note}>{t.label.remaining(remaining)}</p>
    </section>
  );
}

export function LabelPage() {
  const { t } = useI18n();
  const queue = useLabelQueue();
  const current = queue.data?.[0];

  return (
    <>
      <PageHeader
        title={t.label.title}
        description={t.label.desc}
      />
      {queue.isPending && <Loading />}
      {queue.error && <ErrorBlock error={queue.error} onRetry={() => void queue.refetch()} />}
      {queue.isSuccess && !current && (
        <EmptyState icon={<Tags size={28} />} title={t.label.emptyTitle} description={t.label.emptyDesc} />
      )}
      {current && <LabelForm key={current.capture_id} sample={current} remaining={queue.data!.length} />}
    </>
  );
}
