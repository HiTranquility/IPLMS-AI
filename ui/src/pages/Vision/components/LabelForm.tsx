import { Contrast, Layers, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { TextField } from '@/components/common/Ui/form/Field';
import { CropImage } from '@/components/common/Ui/media/CropImage';
import { useAddLabel } from '@/hooks/mutations/useVisionMutations';
import { useI18n } from '@/i18n/I18nProvider';
import type { LabelVerdict, VisionSample } from '@/types/vision';
import { DASH, fmtPercent } from '@/utils/format';
import styles from '../LabelPage.module.css';

export interface LabelFormProps {
  sample: VisionSample;
  remaining: number;
}

export function LabelForm({ sample, remaining }: LabelFormProps) {
  const { t } = useI18n();
  const add = useAddLabel();
  const [correcting, setCorrecting] = useState(false);
  const [plate, setPlate] = useState('');
  const plateRef = useRef<HTMLInputElement>(null);

  // Bộ điều khiển hiển thị ảnh (Zoom & Filters)
  const [zoom, setZoom] = useState(1);
  const [invert, setInvert] = useState(false);
  const [highContrast, setHighContrast] = useState(false);

  const resetViewer = () => {
    setZoom(1);
    setInvert(false);
    setHighContrast(false);
  };

  const send = (verdict: LabelVerdict) =>
    add.mutate({ captureId: sample.capture_id, verdict, plateText: verdict === 'CORRECTED' ? plate : '' });

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

  // Tính toán filter CSS cho ảnh
  const filterStyle = [
    invert ? 'invert(1)' : '',
    highContrast ? 'contrast(200%) brightness(115%)' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <section className={styles.labelCard} aria-label={t.label.card}>
      <div className={styles.cardHeader}>
        <span className={styles.sampleId} title={sample.capture_id}>
          ID: {sample.capture_id.slice(0, 13)}...
        </span>
        <span className={styles.queueBadge}>
          {t.label.remaining(remaining)}
        </span>
      </div>

      {/* Khung soi ảnh biển số với công cụ Zoom & Filter */}
      <div className={styles.viewerBox}>
        <div
          className={styles.imageWrapper}
          style={{
            transform: `scale(${zoom})`,
            filter: filterStyle || undefined,
          }}
        >
          <CropImage captureId={sample.capture_id} size="lg" />
        </div>

        {/* Thanh công cụ soi ảnh */}
        <div className={styles.canvasToolbar} role="toolbar" aria-label="Công cụ soi ảnh">
          <button
            type="button"
            className={styles.toolBtn}
            onClick={() => setZoom((z) => Math.min(z + 0.3, 2.5))}
            title="Phóng to ảnh"
          >
            <ZoomIn size={13} aria-hidden />
          </button>
          <button
            type="button"
            className={styles.toolBtn}
            onClick={() => setZoom((z) => Math.max(z - 0.3, 0.7))}
            title="Thu nhỏ ảnh"
          >
            <ZoomOut size={13} aria-hidden />
          </button>
          <button
            type="button"
            className={`${styles.toolBtn} ${invert ? styles.toolBtnActive : ''}`}
            onClick={() => setInvert(!invert)}
            title="Đảo màu (Invert) — xem biển mờ/chói đèn"
          >
            <Layers size={13} aria-hidden />
          </button>
          <button
            type="button"
            className={`${styles.toolBtn} ${highContrast ? styles.toolBtnActive : ''}`}
            onClick={() => setHighContrast(!highContrast)}
            title="Tăng tương phản (High contrast)"
          >
            <Contrast size={13} aria-hidden />
          </button>
          <button
            type="button"
            className={styles.toolBtn}
            onClick={resetViewer}
            title="Khôi phục ảnh gốc"
          >
            <RotateCcw size={12} aria-hidden />
          </button>
        </div>
      </div>

      <dl className={styles.facts}>
        <dt>{t.label.gatePlate}</dt>
        <dd className={styles.plate}>{sample.confirmed_plate || DASH}</dd>
        <dt>{t.label.machine}</dt>
        <dd className={styles.mono}>
          {sample.machine_plate || DASH} · {fmtPercent(sample.machine_confidence)}
        </dd>
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
          <TextField
            ref={plateRef}
            label={t.label.rightPlate}
            required
            minLength={4}
            maxLength={20}
            value={plate}
            onChange={(e) => setPlate(e.target.value.toUpperCase())}
          />
          <Button type="submit" variant="accent" loading={add.isPending}>
            {t.label.saveFix}
          </Button>
        </form>
      )}

      {add.error && <ErrorBlock error={add.error} />}
    </section>
  );
}

export default LabelForm;
