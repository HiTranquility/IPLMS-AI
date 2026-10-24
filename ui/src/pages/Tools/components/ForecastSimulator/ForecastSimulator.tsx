import { useId, useMemo, useState } from 'react';
import {
  AlertTriangle,
  LineChart,
  Scale,
  ShieldAlert,
  Sliders,
  X,
} from 'lucide-react';
import { SimulatedBanner } from '@/components/common/Ui/feedback/SimulatedBanner';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtInt } from '@/utils/format';
import styles from './ForecastSimulator.module.css';

// Kịch bản lấp đầy minh hoạ theo giờ (0h–23h), KHÔNG phải dự báo: Forecast server chưa có
// model (FeatureNotImplemented). UI gắn nhãn MÔ PHỎNG và ghi rõ trên biểu đồ (ai bug-018).
const LOT_OCCUPANCY_BASELINES: Record<string, number[]> = {
  lot_landmark_81: [
    18, 15, 12, 10, 12, 20, 38, 68, 86, 89, 84, 78,
    74, 79, 83, 85, 87, 91, 93, 88, 76, 58, 40, 25,
  ],
  lot_vincom_center: [
    12, 10, 8, 8, 10, 15, 25, 55, 75, 86, 92, 94,
    90, 88, 84, 85, 89, 93, 95, 94, 88, 72, 45, 22,
  ],
  lot_suburban_hub: [
    22, 16, 12, 10, 15, 30, 65, 92, 94, 85, 70, 62,
    60, 62, 65, 70, 82, 94, 96, 90, 75, 55, 38, 28,
  ],
};

const CHART_W = 600;
const CHART_H = 220;
const PAD = { left: 35, right: 30, top: 20, bottom: 25 };

function createSmoothPath(points: { x: number; y: number }[]): string {
  if (points.length === 0) return '';
  let d = `M ${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i === 0 ? 0 : i - 1];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2 < points.length ? i + 2 : i + 1];

    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;

    d += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
  }
  return d;
}

export function ForecastSimulator() {
  const { t } = useI18n();
  const selectId = useId();

  // Simulation states
  const [lotId, setLotId] = useState<string>('lot_landmark_81');
  const [capacity, setCapacity] = useState<number>(250);
  const [baseRate, setBaseRate] = useState<number>(35000);
  const [surgeThreshold, setSurgeThreshold] = useState<number>(85);
  const [multiplier, setMultiplier] = useState<number>(1.3);
  const [hoveredHour, setHoveredHour] = useState<number | null>(null);
  const [showSafetyModal, setShowSafetyModal] = useState<boolean>(false);

  // Current series based on selected parking lot
  const currentBaseline = LOT_OCCUPANCY_BASELINES[lotId] ?? LOT_OCCUPANCY_BASELINES.lot_landmark_81;

  // KPI Calculations
  const peakHoursCount = useMemo(() => {
    return currentBaseline.filter((rate) => rate >= surgeThreshold).length;
  }, [currentBaseline, surgeThreshold]);

  const suggestedPeakRate = useMemo(() => {
    return Math.round(baseRate * multiplier);
  }, [baseRate, multiplier]);


  // Coordinate mappers
  const getX = (hour: number) => PAD.left + (hour / 23) * (CHART_W - PAD.left - PAD.right);
  const getY = (rate: number) => CHART_H - PAD.bottom - (rate / 100) * (CHART_H - PAD.top - PAD.bottom);

  // SVG Chart points and paths
  const chartPoints = useMemo(() => {
    return currentBaseline.map((rate, hour) => ({
      hour,
      rate,
      x: getX(hour),
      y: getY(rate),
      isPeak: rate >= surgeThreshold,
    }));
  }, [currentBaseline, surgeThreshold]);

  const linePath = useMemo(() => createSmoothPath(chartPoints), [chartPoints]);
  const areaPath = useMemo(() => {
    if (!linePath || chartPoints.length === 0) return '';
    const lastX = chartPoints[chartPoints.length - 1].x.toFixed(1);
    const firstX = chartPoints[0].x.toFixed(1);
    const bottomY = getY(0).toFixed(1);
    return `${linePath} L ${lastX} ${bottomY} L ${firstX} ${bottomY} Z`;
  }, [linePath, chartPoints]);

  const thresholdY = getY(surgeThreshold);

  return (
    <section className={styles.container} aria-labelledby="forecast-heading">
      {/* Banner */}
      <div className={styles.banner}>
        <div className={styles.bannerInfo}>
          <span className={styles.pipelineTag}>Pipeline 3 · Predictive ML</span>
          <h2 id="forecast-heading" className={styles.title}>
            {t.tools.forecastTitle}
          </h2>
          <p className={styles.desc}>{t.tools.forecastDesc}</p>
        </div>
        <div className={styles.safetyBadge}>
          <AlertTriangle size={14} aria-hidden />
          <span>{t.tools.safetyRuleBadge}</span>
        </div>
      </div>

      <SimulatedBanner />

      <div className={styles.mainGrid}>
        {/* Left Column: Simulator Controls */}
        <div className={styles.controlsColumn}>
          <div className={styles.controlCard}>
            <h3 className={styles.controlCardTitle}>
              <Sliders size={16} aria-hidden />
              <span>{t.tools.simParamsTitle}</span>
            </h3>

            {/* Parking Lot Select */}
            <div className={styles.fieldGroup}>
              <label htmlFor={selectId} className={styles.fieldLabel}>
                {t.tools.lotSelect}
              </label>
              <select
                id={selectId}
                className={styles.selectInput}
                value={lotId}
                onChange={(e) => setLotId(e.target.value)}
              >
                <option value="lot_landmark_81">{t.tools.lotLandmark81}</option>
                <option value="lot_vincom_center">{t.tools.lotVincomCenter}</option>
                <option value="lot_suburban_hub">{t.tools.lotSuburbanHub}</option>
              </select>
            </div>

            {/* Capacity Slider */}
            <div className={styles.fieldGroup}>
              <div className={styles.fieldLabelRow}>
                <span className={styles.fieldLabel}>{t.tools.capacity}</span>
                <span className={styles.fieldValue}>
                  {capacity} {t.tools.capacityUnit}
                </span>
              </div>
              <input
                type="range"
                className={styles.rangeInput}
                min={50}
                max={1000}
                step={25}
                value={capacity}
                onChange={(e) => setCapacity(Number(e.target.value))}
                aria-label={t.tools.capacity}
              />
            </div>

            {/* Base Hourly Rate Slider */}
            <div className={styles.fieldGroup}>
              <div className={styles.fieldLabelRow}>
                <span className={styles.fieldLabel}>{t.tools.baseRate}</span>
                <span className={styles.fieldValue}>
                  {fmtInt(baseRate)} {t.tools.baseRateUnit}
                </span>
              </div>
              <input
                type="range"
                className={styles.rangeInput}
                min={10000}
                max={100000}
                step={5000}
                value={baseRate}
                onChange={(e) => setBaseRate(Number(e.target.value))}
                aria-label={t.tools.baseRate}
              />
            </div>

            {/* Surge Threshold Slider */}
            <div className={styles.fieldGroup}>
              <div className={styles.fieldLabelRow}>
                <span className={styles.fieldLabel}>{t.tools.surgeThreshold}</span>
                <span className={styles.fieldValue}>{surgeThreshold}%</span>
              </div>
              <input
                type="range"
                className={styles.rangeInput}
                min={50}
                max={95}
                step={5}
                value={surgeThreshold}
                onChange={(e) => setSurgeThreshold(Number(e.target.value))}
                aria-label={t.tools.surgeThreshold}
              />
            </div>

            {/* Multiplier Slider */}
            <div className={styles.fieldGroup}>
              <div className={styles.fieldLabelRow}>
                <span className={styles.fieldLabel}>{t.tools.surgeMultiplier}</span>
                <span className={styles.fieldValue}>{multiplier.toFixed(2)}x</span>
              </div>
              <input
                type="range"
                className={styles.rangeInput}
                min={1.1}
                max={2.0}
                step={0.05}
                value={multiplier}
                onChange={(e) => setMultiplier(Number(e.target.value))}
                aria-label={t.tools.surgeMultiplier}
              />
            </div>

            {/* Live API Safety Gate Test Button */}
            <button
              type="button"
              className={styles.testApiBtn}
              onClick={() => setShowSafetyModal(true)}
            >
              <ShieldAlert size={14} aria-hidden />
              <span>{t.tools.testApiBtn}</span>
            </button>
          </div>

          {/* ADR-0008 Explanation Card */}
          <div className={styles.adrCard}>
            <div className={styles.adrTitle}>
              <Scale size={16} aria-hidden />
              <span>{t.tools.adr0008Title}</span>
            </div>
            <p className={styles.adrDesc}>{t.tools.adr0008Desc}</p>
          </div>
        </div>

        {/* Right Column: KPIs & 24h Occupancy SVG Chart */}
        <div className={styles.contentColumn}>
          {/* 3 KPI Cards */}
          <div className={styles.kpiRow}>
            <div className={styles.kpiCard}>
              <span className={styles.kpiLabel}>{t.tools.kpiPeakHours}</span>
              <div className={styles.kpiValueRow}>
                <span className={`${styles.kpiValue} ${styles.kpiAccent}`}>
                  {peakHoursCount}
                </span>
                <span className={styles.kpiUnit}>{t.tools.kpiPeakHoursUnit}</span>
              </div>
            </div>

            <div className={styles.kpiCard}>
              <span className={styles.kpiLabel}>{t.tools.kpiSurgeRate}</span>
              <div className={styles.kpiValueRow}>
                <span className={`${styles.kpiValue} ${styles.kpiSuccess}`}>
                  {fmtInt(suggestedPeakRate)}
                </span>
                <span className={styles.kpiUnit}>{t.tools.kpiSurgeRateUnit}</span>
              </div>
            </div>

            <div className={styles.kpiCard}>
              <span className={styles.kpiLabel}>{t.tools.kpiRevenueDiff}</span>
              <div className={styles.kpiValueRow}>
                {/* Chưa có mô hình doanh thu: không dùng hệ số tự đặt. */}
                <span className={`${styles.kpiValue} ${styles.kpiInfo}`}>—</span>
                <span className={styles.kpiUnit}>{t.studio.revenueUnknown}</span>
              </div>
            </div>
          </div>

          {/* 24h Occupancy SVG Chart */}
          <div className={styles.chartCard}>
            <div className={styles.chartHeader}>
              <h3 className={styles.chartTitle}>
                <LineChart size={16} aria-hidden />
                <span>{t.tools.chartTitle}</span>
              </h3>
              <span className={styles.chartBaselineBadge}>{t.tools.chartBaseline}</span>
            </div>

            <div className={styles.chartWrapper}>
              <svg
                viewBox={`0 0 ${CHART_W} ${CHART_H}`}
                className={styles.svgChart}
                role="img"
                aria-label={t.tools.chartTitle}
              >
                {/* Y-axis Grid Lines & Labels */}
                {[0, 25, 50, 75, 100].map((v) => (
                  <g key={`y-${v}`}>
                    <line
                      x1={PAD.left}
                      x2={CHART_W - PAD.right}
                      y1={getY(v)}
                      y2={getY(v)}
                      className={styles.gridLine}
                    />
                    <text
                      x={PAD.left - 6}
                      y={getY(v)}
                      className={`${styles.axisText} ${styles.axisTextY}`}
                    >
                      {v}%
                    </text>
                  </g>
                ))}

                {/* X-axis Labels (every 3 hours) */}
                {[0, 3, 6, 9, 12, 15, 18, 21, 23].map((hour) => (
                  <text
                    key={`x-${hour}`}
                    x={getX(hour)}
                    y={CHART_H - PAD.bottom + 6}
                    className={`${styles.axisText} ${styles.axisTextX}`}
                  >
                    {hour}h
                  </text>
                ))}

                {/* Surge Threshold Line */}
                <line
                  x1={PAD.left}
                  x2={CHART_W - PAD.right}
                  y1={thresholdY}
                  y2={thresholdY}
                  className={styles.thresholdLine}
                />
                <text
                  x={CHART_W - PAD.right - 2}
                  y={thresholdY - 5}
                  className={styles.thresholdLabel}
                >
                  {surgeThreshold}%
                </text>

                {/* Area and Line */}
                <path d={areaPath} className={styles.areaFill} />
                <path d={linePath} className={styles.curveLine} />

                {/* Data Points */}
                {chartPoints.map((pt) => (
                  <circle
                    key={`dot-${pt.hour}`}
                    cx={pt.x}
                    cy={pt.y}
                    r={pt.isPeak ? 4 : 2.5}
                    className={`${styles.dataPoint} ${pt.isPeak ? styles.dataPointPeak : ''}`}
                    onMouseEnter={() => setHoveredHour(pt.hour)}
                    onMouseLeave={() => setHoveredHour(null)}
                  >
                    <title>{`${pt.hour}h: ${pt.rate}% occupancy (${Math.round((capacity * pt.rate) / 100)} slots)`}</title>
                  </circle>
                ))}
              </svg>
            </div>

            {/* Hover details if active */}
            {hoveredHour !== null && (
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text)', display: 'flex', gap: 'var(--space-2)' }}>
                <span>{t.tools.forecastHour(hoveredHour)}</span>
                <strong style={{ color: 'var(--color-accent)' }}>{`${currentBaseline[hoveredHour]}%`}</strong>
                <span style={{ color: 'var(--color-muted)' }}>
                  {`${t.tools.forecastSlots(Math.round((capacity * currentBaseline[hoveredHour]) / 100), capacity)} · ${
                    currentBaseline[hoveredHour] >= surgeThreshold
                      ? t.tools.forecastSurgeRate(fmtInt(suggestedPeakRate))
                      : t.tools.forecastRate(fmtInt(baseRate))
                  }`}
                </span>
              </div>
            )}

            {/* Chart Legend */}
            <div className={styles.chartLegend}>
              <div className={styles.legendItem}>
                <span className={`${styles.legendColorBox} ${styles.legendColorOccupancy}`} />
                <span>{t.tools.chartLegendOccupancy}</span>
              </div>
              <div className={styles.legendItem}>
                <span className={`${styles.legendColorBox} ${styles.legendColorThreshold}`} />
                <span>{`${t.tools.chartLegendThreshold} (≥ ${surgeThreshold}%)`}</span>
              </div>
              <div className={styles.legendItem}>
                <span className={`${styles.legendColorBox} ${styles.legendColorPeak}`} />
                <span>{`${t.tools.kpiPeakHours}: ${peakHoursCount}h`}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ADR-0008 Gate Check Modal */}
      {showSafetyModal && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="modal-adr-title">
          <div className={styles.modalCard}>
            <div className={styles.modalHeader}>
              <h4 id="modal-adr-title" className={styles.modalTitle}>
                <ShieldAlert size={16} aria-hidden />
                <span>{t.tools.adr0008ModalTitle}</span>
              </h4>
              <button
                type="button"
                className={styles.closeBtn}
                onClick={() => setShowSafetyModal(false)}
                aria-label={t.tools.close}
              >
                <X size={16} aria-hidden />
              </button>
            </div>

            <div className={styles.modalContent}>
              <div className={styles.modalStatusRow}>
                <span>{t.tools.adr0008Status}</span>
              </div>
              <p className={styles.modalMessage}>{t.tools.adr0008ServiceMsg}</p>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default ForecastSimulator;
