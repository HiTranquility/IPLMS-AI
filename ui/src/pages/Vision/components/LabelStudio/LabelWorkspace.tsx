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
import type { LabelVerdict, VisionSample } from '@/types/vision';
import { DASH, fmtPercent } from '@/utils/format';
import styles from './LabelStudio.module.css';

export interface LabelWorkspaceProps {
  sample: VisionSample;
  remaining: number;
  onLabeled?: (captureId: string, verdict: LabelVerdict, plateText: string) => void;
}

export function LabelWorkspace({ sample, remaining, onLabeled }: LabelWorkspaceProps) {
  const { t } = useI18n();
  const add = useAddLabel();
  const [correcting, setCorrecting] = useState(false);
  const [plate, setPlate] = useState('');
  const plateRef = useRef<HTMLInputElement>(null);

  // Bộ điều khiển hiển thị ảnh (Zoom & Filters)
  const [zoom, setZoom] = useState(1);
  const [invert, setInvert] = useState(false);
  const [highContrast, setHighContrast] = useState(false);

  // Quality Flags (Thuộc tính chất lượng biển số)
  const [qualityFlags, setQualityFlags] = useState<string[]>([]);

  const toggleFlag = (flag: string) => {
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
      { captureId: sample.capture_id, verdict, plateText: verdict === 'CORRECTED' ? plate : '' },
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

  const availableFlags = [
    { id: 'blurry', label: 'Biển mờ / bụi bẩn' },
    { id: 'glare', label: 'Chói sáng đèn pha' },
    { id: 'skewed', label: 'Góc chụp nghiêng' },
    { id: 'occluded', label: 'Che khuất một phần' },
    { id: 'two_line', label: 'Biển 2 dòng' },
  ];

  return (
    <div className={styles.workspaceGrid}>
      {/* Cột trái: Khung soi ảnh biển số */}
      <section className={styles.viewerCard} aria-label="Khung soi ảnh biển số">
        <div className={styles.viewerHeader}>
          <span>Ảnh cắt từ camera cổng (ANPR ROI)</span>
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
          <div className={styles.floatingToolbar} role="toolbar" aria-label="Bộ công cụ soi ảnh">
            <button
              type="button"
              className={styles.toolButton}
              onClick={() => setZoom((z) => Math.min(z + 0.3, 2.5))}
              title="Phóng to ảnh (+)"
            >
              <ZoomIn size={14} aria-hidden />
            </button>
            <button
              type="button"
              className={styles.toolButton}
              onClick={() => setZoom((z) => Math.max(z - 0.3, 0.7))}
              title="Thu nhỏ ảnh (-)"
            >
              <ZoomOut size={14} aria-hidden />
            </button>
            <button
              type="button"
              className={`${styles.toolButton} ${invert ? styles.toolButtonActive : ''}`}
              onClick={() => setInvert(!invert)}
              title="Đảo màu (I) — soi biển mờ/chói"
            >
              <Layers size={14} aria-hidden />
            </button>
            <button
              type="button"
              className={`${styles.toolButton} ${highContrast ? styles.toolButtonActive : ''}`}
              onClick={() => setHighContrast(!highContrast)}
              title="Tăng tương phản (C)"
            >
              <Contrast size={14} aria-hidden />
            </button>
            <button
              type="button"
              className={styles.toolButton}
              onClick={resetViewer}
              title="Khôi phục ảnh gốc (0)"
            >
              <RotateCcw size={13} aria-hidden />
            </button>
          </div>
        </div>

        {/* Thông tin metadata kỹ thuật */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 'var(--text-xs)', color: 'var(--color-muted)' }}>
          <span>SHA256: {sample.image_sha256?.slice(0, 12)}...</span>
          <span>Hàng đợi còn: {remaining} mẫu</span>
        </div>
      </section>

      {/* Cột phải: Bảng thông tin phán đoán & Thao tác gán nhãn */}
      <section className={styles.formCard} aria-label="Biểu mẫu gán nhãn">
        <div className={styles.formHeader}>
          <div className={styles.sampleMeta}>
            <span>ID: {sample.capture_id.slice(0, 8)}...</span>
            {sample.human_corrected && (
              <Badge tone="accent">Nhân viên cổng đã sửa</Badge>
            )}
          </div>
          <Badge tone="neutral">Còn {remaining} mẫu</Badge>
        </div>

        {/* Hộp so sánh kết quả đọc máy vs cổng */}
        <div className={styles.comparisonBox}>
          <div className={styles.comparisonCol}>
            <span className={styles.comparisonLabel}>Máy nhận diện (AI)</span>
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
            <span className={styles.comparisonLabel}>Ghi nhận tại cổng</span>
            <div className={styles.plateDisplay}>{sample.confirmed_plate || DASH}</div>
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)' }}>
              Trạng thái: {sample.source_status || 'CONFIRMED'}
            </span>
          </div>
        </div>

        {/* Lý do chọn mẫu */}
        {sample.selection_reasons.length > 0 && (
          <div className={styles.reasonsRow}>
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)', marginRight: 4 }}>
              Lý do vào hàng đợi:
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
          <span className={styles.qualityFlagsTitle}>Thuộc tính ảnh / Biển số</span>
          <div className={styles.flagChips}>
            {availableFlags.map((flag) => {
              const active = qualityFlags.includes(flag.id);
              return (
                <button
                  key={flag.id}
                  type="button"
                  className={`${styles.flagChip} ${active ? styles.flagChipActive : ''}`}
                  onClick={() => toggleFlag(flag.id)}
                >
                  <Eye size={12} aria-hidden />
                  {flag.label}
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
            title="Xác nhận biển số máy nhận diện là chính xác 100% [Phím 1]"
          >
            <Check size={14} aria-hidden />
            Đúng 100% <kbd className={styles.kbd}>1</kbd>
          </Button>

          <Button
            variant="secondary"
            onClick={() => setCorrecting((c) => !c)}
            title="Chỉnh sửa lại chuỗi ký tự biển số [Phím 2]"
          >
            <Edit3 size={14} aria-hidden />
            Sửa biển <kbd className={styles.kbd}>2</kbd>
          </Button>

          <Button
            variant="danger"
            onClick={() => send('UNUSABLE')}
            loading={add.isPending && add.variables?.verdict === 'UNUSABLE'}
            title="Đánh dấu ảnh không thể đọc được hoặc bị hỏng [Phím 3]"
          >
            <AlertTriangle size={14} aria-hidden />
            Ảnh hỏng <kbd className={styles.kbd}>3</kbd>
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
              placeholder="VD: 51A-888.88 hoặc 29-B1 999.99"
            />
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <Button type="submit" variant="accent" loading={add.isPending}>
                {t.label.saveFix}
              </Button>
              <Button type="button" variant="secondary" onClick={() => setCorrecting(false)}>
                Hủy
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
