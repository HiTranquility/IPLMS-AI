import type { AccuracyPoint } from '@/api/types';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtPercent } from '@/utils/format';
import styles from './ThresholdCurve.module.css';

// Toạ độ trong viewBox SVG (không phải px CSS): khung tự co theo bề ngang.
const W = 320;
const H = 160;
const PAD = { left: 30, right: 14, top: 8, bottom: 18 };
const X_MIN = 0.5;
const X_MAX = 1;

// Cỡ chữ trục theo đơn vị viewBox.
const AXIS_FONT = 8;

const x = (t: number) => PAD.left + ((t - X_MIN) / (X_MAX - X_MIN)) * (W - PAD.left - PAD.right);
const y = (v: number) => H - PAD.bottom - v * (H - PAD.top - PAD.bottom);

/** Chia đường tại điểm thiếu số (ngưỡng không còn mẫu) thay vì nối bừa qua khoảng trống. */
function segments(curve: AccuracyPoint[], pick: (p: AccuracyPoint) => number | null): string[] {
  const out: string[] = [];
  let current: string[] = [];
  for (const p of curve) {
    const v = pick(p);
    if (v === null) {
      if (current.length > 1) out.push(current.join(' '));
      current = [];
      continue;
    }
    current.push(`${x(p.threshold).toFixed(1)},${y(v).toFixed(1)}`);
  }
  if (current.length > 1) out.push(current.join(' '));
  return out;
}

/**
 * Đường cong ngưỡng tự nhận: độ chính xác của ảnh ≥ ngưỡng và tỉ lệ ảnh được tự nhận.
 * Bảng số vẫn hiện bên dưới — biểu đồ chỉ giúp nhìn nhanh chỗ đánh đổi.
 */
export function ThresholdCurve({ curve, suggested, target }: { curve: AccuracyPoint[]; suggested: number | null; target: number }) {
  const { t } = useI18n();
  const points = curve.filter((p) => p.threshold >= X_MIN && p.threshold <= X_MAX);
  const accuracy = segments(points, (p) => p.accuracy);
  const coverage = segments(points, (p) => p.coverage);
  if (!accuracy.length && !coverage.length) return null;

  const at = suggested === null ? null : points.find((p) => p.threshold === suggested);
  const summary = at
    ? t.curve.summary(at.threshold.toFixed(2), fmtPercent(at.accuracy), fmtPercent(at.coverage))
    : t.curve.noSuggestion;

  return (
    <figure className={styles.figure}>
      <svg viewBox={`0 0 ${W} ${H}`} className={styles.chart} role="img" aria-label={t.curve.aria(summary)}>
        {[0, 0.5, 1].map((v) => (
          <g key={v}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(v)} y2={y(v)} className={styles.grid} />
            <text x={PAD.left - 4} y={y(v)} fontSize={AXIS_FONT} className={styles.axisY}>{`${v * 100}%`}</text>
          </g>
        ))}
        {[0.5, 0.75, 1].map((t) => (
          <text key={t} x={x(t)} y={H - 5} fontSize={AXIS_FONT} className={styles.axisX}>{t.toFixed(2)}</text>
        ))}
        <line x1={PAD.left} x2={W - PAD.right} y1={y(target)} y2={y(target)} className={styles.target} />
        {suggested !== null && (
          <line x1={x(suggested)} x2={x(suggested)} y1={PAD.top} y2={H - PAD.bottom} className={styles.suggested} />
        )}
        {coverage.map((pts) => <polyline key={`c${pts}`} points={pts} className={styles.coverage} />)}
        {accuracy.map((pts) => <polyline key={`a${pts}`} points={pts} className={styles.accuracy} />)}
      </svg>
      <figcaption className={styles.legend}>
        <span><Swatch className={styles.accuracy} />{t.curve.accuracy}</span>
        <span><Swatch className={styles.coverage} />{t.curve.coverage}</span>
        <span><Swatch className={styles.target} />{t.curve.target(fmtPercent(target))}</span>
        {suggested !== null && <span><Swatch className={styles.suggested} />{t.curve.suggested(suggested.toFixed(2))}</span>}
      </figcaption>
    </figure>
  );
}

function Swatch({ className }: { className: string }) {
  return (
    <svg viewBox="0 0 24 6" className={styles.swatch} aria-hidden>
      <line x1={0} x2={24} y1={3} y2={3} className={className} />
    </svg>
  );
}
