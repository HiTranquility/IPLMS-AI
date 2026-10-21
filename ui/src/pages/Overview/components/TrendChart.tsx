import { useMemo, useState } from 'react';
import { useI18n } from '@/i18n/I18nProvider';
import type { UsageDay } from '@/types/copilot';
import { fmtDay, fmtInt, fmtMs } from '@/utils/format';
import styles from './TrendChart.module.css';

export interface TrendChartProps {
  days: UsageDay[];
}

export function TrendChart({ days }: TrendChartProps) {
  const { t } = useI18n();
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  // Kích thước SVG cố định viewBox
  const width = 640;
  const height = 220;
  const padTop = 20;
  const padBottom = 30;
  const padLeft = 40;
  const padRight = 45;

  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  const { maxReq, maxLatency, points } = useMemo(() => {
    if (!days || days.length === 0) {
      return { maxReq: 1, maxLatency: 1, points: [] };
    }

    const maxR = Math.max(...days.map((d) => d.requests), 5);
    const maxL = Math.max(...days.map((d) => d.avg_latency_ms), 500);

    const count = days.length;
    const step = count > 1 ? chartW / count : chartW;
    const barW = Math.max(Math.min(step * 0.55, 32), 8);

    const calculated = days.map((d, i) => {
      const cx = padLeft + i * step + step / 2;
      const success = Math.max(0, d.requests - d.refused - d.errors);

      const hSuccess = (success / maxR) * chartH;
      const hRefused = (d.refused / maxR) * chartH;
      const hError = (d.errors / maxR) * chartH;

      const yBottom = padTop + chartH;
      const ySuccess = yBottom - hSuccess;
      const yRefused = ySuccess - hRefused;
      const yError = yRefused - hError;

      const yLatency = padTop + chartH - (d.avg_latency_ms / maxL) * chartH;

      return {
        day: d,
        cx,
        barW,
        xBar: cx - barW / 2,
        ySuccess,
        hSuccess,
        yRefused,
        hRefused,
        yError,
        hError,
        yLatency: Math.max(padTop, Math.min(yBottom, yLatency)),
      };
    });

    return { maxReq: maxR, maxLatency: maxL, points: calculated };
  }, [days, chartW, chartH, padLeft, padTop]);

  if (!days || days.length === 0) {
    return (
      <div className={styles.chartContainer}>
        <p className={styles.emptyNotice}>{t.overview.chartNoData}</p>
      </div>
    );
  }

  // Tạo đường dẫn SVG polyline cho độ trễ
  const latencyPath = points.map((p) => `${p.cx},${p.yLatency}`).join(' ');

  const activeDay = hoveredIdx !== null ? points[hoveredIdx]?.day : points[points.length - 1]?.day;

  return (
    <div className={styles.chartContainer}>
      <div className={styles.header}>
        <div className={styles.titleBox}>
          <h3 className={styles.title}>{t.overview.chartTitle}</h3>
          <span className={styles.subtitle}>{t.overview.chartSubtitle}</span>
        </div>

        <div className={styles.legend}>
          <span className={styles.legendItem}>
            <span className={styles.legendDot} style={{ background: 'var(--color-success)' }} />
            {t.overview.chartRequestsLegend}
          </span>
          <span className={styles.legendItem}>
            <span className={styles.legendDot} style={{ background: 'var(--color-warning)' }} />
            {t.overview.chartRefusedLegend}
          </span>
          <span className={styles.legendItem}>
            <span className={styles.legendDot} style={{ background: 'var(--color-danger)' }} />
            {t.overview.chartErrorsLegend}
          </span>
          <span className={styles.legendItem}>
            <span className={styles.legendLine} style={{ background: 'var(--color-accent)' }} />
            {t.overview.chartLatencyLegend}
          </span>
        </div>
      </div>

      <div className={styles.svgWrap}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className={styles.svg}
          role="img"
          aria-label={t.overview.chartTitle}
        >
          {/* Lưới ngang tham chiếu */}
          {[0, 0.5, 1].map((ratio) => {
            const y = padTop + chartH * (1 - ratio);
            const reqVal = Math.round(maxReq * ratio);
            const latVal = Math.round(maxLatency * ratio);
            return (
              <g key={ratio}>
                <line x1={padLeft} y1={y} x2={width - padRight} y2={y} className={styles.gridLine} />
                <text x={padLeft - 6} y={y + 3} textAnchor="end" className={styles.axisText}>
                  {reqVal}
                </text>
                <text x={width - padRight + 6} y={y + 3} textAnchor="start" className={styles.axisText}>
                  {latVal}ms
                </text>
              </g>
            );
          })}

          {/* Cột dữ liệu từng ngày */}
          {points.map((p, idx) => (
            <g
              key={p.day.date}
              className={styles.barGroup}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
              style={{ cursor: 'pointer' }}
            >
              {/* Vùng cảm ứng chuột rộng hơn */}
              <rect
                x={p.cx - p.barW}
                y={padTop}
                width={p.barW * 2}
                height={chartH}
                fill="transparent"
              />

              {/* Stack 1: Thành công */}
              {p.hSuccess > 0 && (
                <rect
                  x={p.xBar}
                  y={p.ySuccess}
                  width={p.barW}
                  height={p.hSuccess}
                  rx={2}
                  className={styles.barSuccess}
                />
              )}

              {/* Stack 2: Bị chặn (Refused) */}
              {p.hRefused > 0 && (
                <rect
                  x={p.xBar}
                  y={p.yRefused}
                  width={p.barW}
                  height={p.hRefused}
                  className={styles.barRefused}
                />
              )}

              {/* Stack 3: Lỗi (Error) */}
              {p.hError > 0 && (
                <rect
                  x={p.xBar}
                  y={p.yError}
                  width={p.barW}
                  height={p.hError}
                  className={styles.barError}
                />
              )}

              {/* Nhãn ngày X-axis */}
              <text
                x={p.cx}
                y={height - padBottom + 16}
                textAnchor="middle"
                className={styles.axisText}
              >
                {fmtDay(p.day.date).slice(0, 5)}
              </text>
            </g>
          ))}

          {/* Đường độ trễ Latency overlay */}
          {points.length > 1 && (
            <polyline points={latencyPath} className={styles.latencyLine} />
          )}

          {/* Điểm nút tròn trên đường độ trễ */}
          {points.map((p, idx) => (
            <circle
              key={`dot-${p.day.date}`}
              cx={p.cx}
              cy={p.yLatency}
              r={hoveredIdx === idx ? 4.5 : 3}
              className={styles.latencyDot}
            />
          ))}
        </svg>
      </div>

      {activeDay && (
        <div className={styles.tooltip}>
          <span>
            <strong>{fmtDay(activeDay.date)}:</strong> {fmtInt(activeDay.requests)} lượt hỏi (
            <span style={{ color: 'var(--color-success)' }}>
              {fmtInt(Math.max(0, activeDay.requests - activeDay.refused - activeDay.errors))} đúng
            </span>
            {activeDay.refused > 0 && (
              <span style={{ color: 'var(--color-warning)' }}> · {fmtInt(activeDay.refused)} chặn</span>
            )}
            {activeDay.errors > 0 && (
              <span style={{ color: 'var(--color-danger)' }}> · {fmtInt(activeDay.errors)} lỗi</span>
            )}
            )
          </span>
          <span style={{ color: 'var(--color-accent-dark)', fontWeight: 600 }}>
            {t.overview.avgLatency}: {fmtMs(activeDay.avg_latency_ms)}
          </span>
        </div>
      )}
    </div>
  );
}

export default TrendChart;
