import {
  AlertTriangle,
  Check,
  Contrast,
  Edit3,
  Eye,
  Layers,
  RotateCcw,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { TextField } from '@/components/common/Ui/form/Field';
import { CropImage } from '@/components/common/Ui/media/CropImage';
import { useAddLabel } from '@/hooks/mutations/useVisionMutations';
import { useI18n } from '@/i18n/I18nProvider';
import { QUALITY_FLAGS, type LabelVerdict, type QualityFlag, type VisionSample } from '@/types/vision';
import { DASH, fmtPercent } from '@/utils/format';
import styles from './LabelStudio.module.css';

export interface LabelWorkspaceProps {
  sample: VisionSample;
  remaining: number;
  onLabeled?: (captureId: string, verdict: LabelVerdict, plateText: string) => void;
}

export function LabelWorkspace({ sample, remaining, onLabeled }: LabelWorkspaceProps) {
  const { t } = useI18n();
  const w = t.label.workspace;
  const add = useAddLabel();
  const [correcting, setCorrecting] = useState(false);
  const [plate, setPlate] = useState('');
  const plateRef = useRef<HTMLInputElement>(null);

  // Bộ điều khiển hiển thị ảnh (Zoom & Filters)
  const [zoom, setZoom] = useState(1);
  const [invert, setInvert] = useState(false);
  const [highContrast, setHighContrast] = useState(false);

  // Cờ điều kiện ảnh: gửi cùng nhãn, lưu ở vision_label.quality_flags (bug-022)
  const [qualityFlags, setQualityFlags] = useState<QualityFlag[]>([]);

  const toggleFlag = (flag: QualityFlag) => {
    setQualityFlags((prev) =>
      prev.includes(flag) ? prev.filter((f) => f !== flag) : [...prev, flag],
    );
  };

  const resetViewer = () => {
    setZoom(1);
    setInvert(false);
    setHighContrast(false);
  };

  const send = (verdict: LabelVerdict) => {
    const finalPlate = verdict === 'CORRECTED' ? plate : sample.machine_plate;
    add.mutate(
      {
        captureId: sample.capture_id,
        verdict,
        plateText: verdict === 'CORRECTED' ? plate : '',
        qualityFlags,
      },
      {
        onSuccess: () => {
          onLabeled?.(sample.capture_id, verdict, finalPlate);
          setCorrecting(false);
          setPlate('');
          resetViewer();
          setQualityFlags([]);
        },
      },
    );
  };

  // Keyboard Shortcuts: 1 đúng · 2 sửa · 3 hỏng · I đảo màu · C tương phản · 0 reset · +/- zoom
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (add.isPending || target?.closest('input, textarea, select')) return;

      if (event.key === '1') {
        event.preventDefault();
        send('CORRECT');
      } else if (event.key === '2') {
        event.preventDefault();
        setCorrecting(true);
      } else if (event.key === '3') {
        event.preventDefault();
        send('UNUSABLE');
      } else if (event.key === 'i' || event.key === 'I') {
        event.preventDefault();
        setInvert((v) => !v);
      } else if (event.key === 'c' || event.key === 'C') {
        event.preventDefault();
        setHighContrast((v) => !v);
      } else if (event.key === '0') {
        event.preventDefault();
        resetViewer();
      } else if (event.key === '+' || event.key === '=') {
        event.preventDefault();
        setZoom((z) => Math.min(z + 0.3, 2.5));
      } else if (event.key === '-' || event.key === '_') {
        event.preventDefault();
        setZoom((z) => Math.max(z - 0.3, 0.7));
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  useEffect(() => {
    if (correcting) {
      setPlate('');
      plateRef.current?.focus();
    }
  }, [correcting]);

  const submitCorrection = (event: FormEvent) => {
    event.preventDefault();
    if (plate.trim()) {
      send('CORRECTED');
    }
  };

  const filterStyle = [
    invert ? 'invert(1)' : '',
    highContrast ? 'contrast(200%) brightness(115%)' : '',
  ]
    .filter(Boolean)
    .join(' ');

  const confidence = sample.machine_confidence ?? 0;
  const confPercent = Math.round(confidence * 100);
  const confColor =
    confidence >= 0.9
      ? 'var(--color-success)'
      : confidence >= 0.75
      ? 'var(--color-warning)'
      : 'var(--color-danger)';

  return (
    <div className={styles.workspaceGrid}>
      {/* Cột trái: Khung soi ảnh biển số */}
      <section className={styles.viewerCard} aria-label={w.viewerRegion}>
        <div className={styles.viewerHeader}>
          <span>{w.viewerTitle}</span>
          <span style={{ fontFamily: 'var(--font-mono)' }}>Zoom: {Math.round(zoom * 100)}%</span>
        </div>

        <div className={styles.viewerCanvasBox}>
          <div
            className={styles.imageViewport}
            style={{
              transform: `scale(${zoom})`,
              filter: filterStyle || undefined,
            }}
          >
            <CropImage captureId={sample.capture_id} size="lg" />
          </div>

          {/* Thanh công cụ nổi trên ảnh */}
          <div className={styles.floatingToolbar} role="toolbar" aria-label={w.toolbar}>
            <button
              type="button"
              className={styles.toolButton}
              onClick={() => setZoom((z) => Math.min(z + 0.3, 2.5))}
              title={w.zoomIn}
            >
              <ZoomIn size={14} aria-hidden />
            </button>
            <button
              type="button"
              className={styles.toolButton}
              onClick={() => setZoom((z) => Math.max(z - 0.3, 0.7))}
              title={w.zoomOut}
            >
              <ZoomOut size={14} aria-hidden />
            </button>
            <button
              type="button"
              className={`${styles.toolButton} ${invert ? styles.toolButtonActive : ''}`}
              onClick={() => setInvert(!invert)}
              title={w.invert}
            >
              <Layers size={14} aria-hidden />
            </button>
            <button
              type="button"
              className={`${styles.toolButton} ${highContrast ? styles.toolButtonActive : ''}`}
              onClick={() => setHighContrast(!highContrast)}
              title={w.contrast}
            >
              <Contrast size={14} aria-hidden />
            </button>
            <button
              type="button"
              className={styles.toolButton}
              onClick={resetViewer}
              title={w.reset}
            >
              <RotateCcw size={13} aria-hidden />
            </button>
          </div>
        </div>

        {/* Thông tin metadata kỹ thuật */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 'var(--text-xs)', color: 'var(--color-muted)' }}>
          <span>SHA256: {sample.image_sha256?.slice(0, 12)}...</span>
          <span>{w.queueLeft(remaining)}</span>
        </div>
      </section>

      {/* Cột phải: Bảng thông tin phán đoán & Thao tác gán nhãn */}
      <section className={styles.formCard} aria-label={w.formRegion}>
        <div className={styles.formHeader}>
          <div className={styles.sampleMeta}>
            <span title={sample.capture_id}>ID: {sample.capture_id.slice(0, 8)}…</span>
            {sample.human_corrected && (
              <Badge tone="accent">{w.staffFixed}</Badge>
            )}
          </div>
          <Badge tone="neutral">{w.left(remaining)}</Badge>
        </div>

        {/* Hộp so sánh kết quả đọc máy vs cổng */}
        <div className={styles.comparisonBox}>
          <div className={styles.comparisonCol}>
            <span className={styles.comparisonLabel}>{w.machineAi}</span>
            <div className={styles.plateDisplay}>{sample.machine_plate || DASH}</div>
            <div className={styles.confBar}>
              <div className={styles.confTrack}>
                <div
                  className={styles.confFill}
                  style={{ width: `${confPercent}%`, backgroundColor: confColor }}
                />
              </div>
              <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: confColor }}>
                {fmtPercent(sample.machine_confidence)}
              </span>
            </div>
          </div>

          <div className={styles.comparisonCol}>
            <span className={styles.comparisonLabel}>{w.atGate}</span>
            <div className={styles.plateDisplay}>{sample.confirmed_plate || DASH}</div>
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)' }}>
              {w.sourceStatus(sample.source_status || 'CONFIRMED')}
            </span>
          </div>
        </div>

        {/* Lý do chọn mẫu */}
        {sample.selection_reasons.length > 0 && (
          <div className={styles.reasonsRow}>
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)', marginRight: 4 }}>
              {w.queueReasons}
            </span>
            {sample.selection_reasons.map((r) => (
              <Badge key={r} tone="neutral">
                {t.vision.reason[r] ?? r}
              </Badge>
            ))}
          </div>
        )}

        {/* Thuộc tính chất lượng (Quality Flags) */}
        <div className={styles.qualityFlagsBox}>
          <span className={styles.qualityFlagsTitle}>{t.label.flagsTitle}</span>
          <div className={styles.flagChips}>
            {QUALITY_FLAGS.map((flag) => {
              const active = qualityFlags.includes(flag);
              return (
                <button
                  key={flag}
                  type="button"
                  aria-pressed={active}
                  className={`${styles.flagChip} ${active ? styles.flagChipActive : ''}`}
                  onClick={() => toggleFlag(flag)}
                >
                  <Eye size={12} aria-hidden />
                  {t.label.flags[flag]}
                </button>
              );
            })}
          </div>
        </div>

        {/* Hành động chính: 1 Đúng · 2 Sửa · 3 Hỏng */}
        <div className={styles.primaryActions}>
          <Button
            variant="primary"
            onClick={() => send('CORRECT')}
            loading={add.isPending && add.variables?.verdict === 'CORRECT'}
            title={w.correctTitle}
          >
            <Check size={14} aria-hidden />
            {w.correct100} <kbd className={styles.kbd}>1</kbd>
          </Button>

          <Button
            variant="secondary"
            onClick={() => setCorrecting((c) => !c)}
            title={w.fixTitle}
          >
            <Edit3 size={14} aria-hidden />
            {t.label.fix} <kbd className={styles.kbd}>2</kbd>
          </Button>

          <Button
            variant="danger"
            onClick={() => send('UNUSABLE')}
            loading={add.isPending && add.variables?.verdict === 'UNUSABLE'}
            title={w.unusableTitle}
          >
            <AlertTriangle size={14} aria-hidden />
            {t.label.unusable} <kbd className={styles.kbd}>3</kbd>
          </Button>
        </div>

        {/* Form nhập biển số chỉnh sửa */}
        {correcting && (
          <form className={styles.correctionForm} onSubmit={submitCorrection}>
            <TextField
              ref={plateRef}
              label={t.label.rightPlate}
              required
              minLength={4}
              maxLength={20}
              value={plate}
              onChange={(e) => setPlate(e.target.value.toUpperCase())}
              placeholder={w.platePlaceholder}
            />
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <Button type="submit" variant="accent" loading={add.isPending}>
                {t.label.saveFix}
              </Button>
              <Button type="button" variant="secondary" onClick={() => setCorrecting(false)}>
                {t.review.cancel}
              </Button>
            </div>
          </form>
        )}

        {add.error && <ErrorBlock error={add.error} />}
      </section>
    </div>
  );
}

export default LabelWorkspace;
