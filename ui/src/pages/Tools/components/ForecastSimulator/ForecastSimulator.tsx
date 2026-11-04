import { useId, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Cpu,
  Database,
  LineChart,
  Play,
  Scale,
  ShieldAlert,
  Sliders,
  Sparkles,
  X,
} from 'lucide-react';
import { apiClient } from '@/api/client';
import table from '@/components/common/Ui/data-display/table.module.css';
import { SimulatedBanner } from '@/components/common/Ui/feedback/SimulatedBanner';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { useI18n } from '@/i18n/I18nProvider';
import { DASH, fmtInt } from '@/utils/format';
import { useForecastAreas } from '@/hooks/queries';
import styles from './ForecastSimulator.module.css';

interface FeatureRow {
  day_of_week: number;
  hour_of_day: number;
  is_weekend: number;
  total_slots: number;
  hour_sin: number;
  hour_cos: number;
  dow_sin: number;
  dow_cos: number;
  occupancy_pct: number;
}

interface PipelineSimulateResponse {
  stage1_datalake: {
    source_path: string;
    is_fallback: boolean;
    total_records: number;
    area_ids: string[];
    weekly_profile: Record<string, number>;
  };
  stage2_features: {
    feature_names: string[];
    total_samples: number;
    prophet_points: number;
    sample_rows: FeatureRow[];
  };
  stage3_inference: {
    area_id: string;
    day_of_week: number;
    model_version: string;
    is_fallback: boolean;
    peak_hour: number;
    peak_occupancy_pct: number;
    recommended_surge_multiplier: number;
    hourly_predictions: {
      hour_of_day: number;
      predicted_occupancy_pct: number;
      estimated_free_spots: number;
      surge_multiplier: number;
      confidence: number;
    }[];
    surge_quote: {
      area_id: string;
      occupancy_pct?: number;
      current_occupancy_pct?: number;
      surge_multiplier: number;
      effective_hourly_rate: number;
      reason_code?: string;
      reason?: string;
    };
  };
}

// Illustrative 24h occupancy curve (0h-23h) when backend pipeline has not been synced yet.
const ILLUSTRATIVE_CURVE: number[] = [
  18, 15, 12, 10, 12, 20, 38, 68, 86, 89, 84, 78,
  74, 79, 83, 85, 87, 91, 93, 88, 76, 58, 40, 25,
];

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

  // Simulation states backed by Gold lake areas
  const lakeAreasQuery = useForecastAreas();
  const lakeAreas = lakeAreasQuery.data?.areas ?? [];
  const [pickedLot, setLotId] = useState<string>('');
  const lotId = pickedLot || (lakeAreas[0]?.area_id ?? '');
  const [dayOfWeek, setDayOfWeek] = useState<number>(4);
  const [capacity, setCapacity] = useState<number>(250);
  const [baseRate, setBaseRate] = useState<number>(35000);
  const [surgeThreshold, setSurgeThreshold] = useState<number>(85);
  const [multiplier, setMultiplier] = useState<number>(1.3);
  const [hoveredHour, setHoveredHour] = useState<number | null>(null);
  const [showSafetyModal, setShowSafetyModal] = useState<boolean>(false);
  const [pipelineData, setPipelineData] = useState<PipelineSimulateResponse | null>(null);
  const [syncingPipeline, setSyncingPipeline] = useState<boolean>(false);

  const currentBaseline = useMemo(() => {
    if (pipelineData?.stage3_inference?.hourly_predictions?.length === 24) {
      return pipelineData.stage3_inference.hourly_predictions.map((p) =>
        Math.round(p.predicted_occupancy_pct),
      );
    }
    return ILLUSTRATIVE_CURVE;
  }, [pipelineData]);

  const computedFeatureRows = useMemo<FeatureRow[]>(() => {
    if (pipelineData?.stage2_features?.sample_rows?.length) {
      return pipelineData.stage2_features.sample_rows;
    }
    const keyHours = [8, 12, 18, 21];
    return keyHours.map((h) => ({
      day_of_week: dayOfWeek,
      hour_of_day: h,
      is_weekend: dayOfWeek >= 5 ? 1 : 0,
      total_slots: capacity,
      hour_sin: Number(Math.sin((2 * Math.PI * h) / 24).toFixed(4)),
      hour_cos: Number(Math.cos((2 * Math.PI * h) / 24).toFixed(4)),
      dow_sin: Number(Math.sin((2 * Math.PI * dayOfWeek) / 7).toFixed(4)),
      dow_cos: Number(Math.cos((2 * Math.PI * dayOfWeek) / 7).toFixed(4)),
      occupancy_pct: currentBaseline[h] ?? 50,
    }));
  }, [pipelineData, dayOfWeek, capacity, currentBaseline]);

  const weeklyProfile = useMemo(() => {
    if (pipelineData?.stage1_datalake?.weekly_profile) {
      return [0, 1, 2, 3, 4, 5, 6].map((d) => ({
        day: d,
        avg: pipelineData.stage1_datalake.weekly_profile[String(d)] ?? 60,
      }));
    }
    const baseAvg = [61.2, 62.5, 63.1, 64.0, 68.4, 54.8, 51.6];
    return baseAvg.map((avg, d) => ({ day: d, avg }));
  }, [pipelineData]);

  const runBackendPipeline = async (nextDay?: number, nextLot?: string) => {
    const targetDay = nextDay ?? dayOfWeek;
    const targetLot = nextLot ?? lotId;
    if (!targetLot) return;
    setSyncingPipeline(true);
    try {
      const item = await apiClient.postOne<PipelineSimulateResponse>('/tools/forecast/simulate', {
        area_id: targetLot,
        day_of_week: targetDay,
        total_capacity: capacity,
        base_hourly_rate: baseRate,
      });
      if (item) {
        setPipelineData(item);
        if (item.stage3_inference?.recommended_surge_multiplier >= 1.1) {
          setMultiplier(item.stage3_inference.recommended_surge_multiplier);
        }
      }
    } catch {
      // Keep local simulation state if backend call fails
    } finally {
      setSyncingPipeline(false);
    }
  };

  const peakHoursCount = useMemo(() => {
    return currentBaseline.filter((rate) => rate >= surgeThreshold).length;
  }, [currentBaseline, surgeThreshold]);

  const suggestedPeakRate = useMemo(() => {
    return Math.round(baseRate * multiplier);
  }, [baseRate, multiplier]);

  const getX = (hour: number) => PAD.left + (hour / 23) * (CHART_W - PAD.left - PAD.right);
  const getY = (rate: number) => CHART_H - PAD.bottom - (rate / 100) * (CHART_H - PAD.top - PAD.bottom);

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
          <span className={styles.pipelineTag}>{t.tools.pipeline3Badge}</span>
          <h2 id="forecast-heading" className={styles.title}>
            {t.tools.forecastTitle}
          </h2>
          <p className={styles.desc}>{t.tools.pipeline3Sub}</p>
        </div>
        <div className={styles.safetyBadge}>
          <AlertTriangle size={14} aria-hidden />
          <span>{t.tools.safetyRuleBadge}</span>
        </div>
      </div>

      <SimulatedBanner />

      {/* 3-Stage ML Pipeline Architecture Cards */}
      <div className={styles.pipelineGrid}>
        <div className={styles.stageCard}>
          <div className={styles.stageCardHeader}>
            <span className={styles.stageIconWrap}>
              <Database size={16} aria-hidden />
            </span>
            <strong className={styles.stageTitle}>{t.tools.stage1Title}</strong>
          </div>
          <p className={styles.stageSub}>{t.tools.stage1Sub}</p>
          <div className={styles.stageMetaList}>
            <div>
              <span className={styles.stageMetaLabel}>{t.tools.stage1Source} </span>
              <code>{pipelineData?.stage1_datalake.source_path ?? 'analytic/var/datalake/gold/occupancy'}</code>
            </div>
            <div>
              <span className={styles.stageMetaLabel}>{t.tools.stage1Records} </span>
              <strong className="num">{pipelineData ? fmtInt(pipelineData.stage1_datalake.total_records) : DASH}</strong>
              <span> (7 × 24h)</span>
            </div>
          </div>
        </div>

        <div className={styles.stageCard}>
          <div className={styles.stageCardHeader}>
            <span className={styles.stageIconWrap}>
              <Cpu size={16} aria-hidden />
            </span>
            <strong className={styles.stageTitle}>{t.tools.stage2Title}</strong>
          </div>
          <p className={styles.stageSub}>{t.tools.stage2Sub}</p>
          <div className={styles.stageMetaList}>
            <div>
              <span className={styles.stageMetaLabel}>{t.tools.stage2Features} </span>
              <code>day_of_week, hour_of_day, is_weekend, total_slots, hour_sin/cos, dow_sin/cos</code>
            </div>
            <div>
              <span className={styles.stageMetaLabel}>{t.tools.stage2Prophet} </span>
              <strong className="num">{pipelineData ? fmtInt(pipelineData.stage2_features.prophet_points) : DASH}</strong>
              <span> (ds, y)</span>
            </div>
          </div>
        </div>

        <div className={styles.stageCard}>
          <div className={styles.stageCardHeader}>
            <span className={styles.stageIconWrap}>
              <Sparkles size={16} aria-hidden />
            </span>
            <strong className={styles.stageTitle}>{t.tools.stage3Title}</strong>
          </div>
          <p className={styles.stageSub}>{t.tools.stage3Sub}</p>
          <div className={styles.stageMetaList}>
            <div>
              <span className={styles.stageMetaLabel}>{t.tools.stage3ModelVer} </span>
              <code>{pipelineData?.stage3_inference.model_version ?? DASH}</code>
            </div>
            <div>
              <span className={styles.stageMetaLabel}>{t.tools.dataSourceLabel} </span>
              <strong>
                {!pipelineData
                  ? t.tools.dataSourceLocalSim
                  : pipelineData.stage3_inference.is_fallback
                    ? t.tools.dataSourceBaseline
                    : t.tools.dataSourceLake}
              </strong>
            </div>
            <div>
              <span className={styles.stageMetaLabel}>{t.tools.stage3Reason} </span>
              <code>
                {pipelineData?.stage3_inference.surge_quote.reason_code ??
                  pipelineData?.stage3_inference.surge_quote.reason ??
                  (peakHoursCount > 0 ? 'PEAK_CONGESTION_SURGE_85_PLUS' : 'NORMAL_TARIFF')}
              </code>
            </div>
          </div>
        </div>
      </div>

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
                onChange={(e) => {
                  setLotId(e.target.value);
                  setPipelineData(null);
                }}
              >
                {lakeAreas.length === 0 && (
                  <option value="" disabled>
                    {lakeAreasQuery.isLoading
                      ? t.feedback.loading
                      : lakeAreasQuery.isError
                        ? t.feedback.loadFailed
                        : t.tools.lakeAreasEmpty}
                  </option>
                )}
                {lakeAreas.map((area) => (
                  <option key={area.area_id} value={area.area_id}>
                    {t.tools.lakeAreaOption(area.area_id, area.records)}
                  </option>
                ))}
              </select>
              {lakeAreasQuery.isError && (
                <ErrorBlock error={lakeAreasQuery.error} onRetry={() => void lakeAreasQuery.refetch()} />
              )}
            </div>

            {/* Day of Week Selector */}
            <div className={styles.fieldGroup}>
              <span className={styles.fieldLabel}>{t.tools.dayLabel}</span>
              <div className={styles.dayBtnGroup}>
                {t.tools.dayNames.map((name, idx) => (
                  <button
                    key={name}
                    type="button"
                    aria-pressed={dayOfWeek === idx}
                    className={`${styles.dayBtn} ${dayOfWeek === idx ? styles.dayBtnActive : ''}`}
                    onClick={() => {
                      setDayOfWeek(idx);
                      if (pipelineData) void runBackendPipeline(idx, lotId);
                    }}
                  >
                    {name}
                  </button>
                ))}
              </div>
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

            {/* Run Pipeline 3 on Backend Button */}
            <button
              type="button"
              className={styles.primarySyncBtn}
              onClick={() => void runBackendPipeline()}
              disabled={syncingPipeline || !lotId}
            >
              <Play size={14} aria-hidden />
              <span>{syncingPipeline ? t.tools.syncingBackend : t.tools.syncBackendBtn}</span>
            </button>

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

          {/* ADR-0008 Safety Principle Card */}
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

                <path d={areaPath} className={styles.areaFill} />
                <path d={linePath} className={styles.curveLine} />

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

            {hoveredHour !== null && (
              <div className={styles.hoverReadoutBar}>
                <span>{t.tools.forecastHour(hoveredHour)}</span>
                <strong className={styles.hoverReadoutStrong}>{`${currentBaseline[hoveredHour]}%`}</strong>
                <span className={styles.hoverReadoutMuted}>
                  {`${t.tools.forecastSlots(Math.round((capacity * currentBaseline[hoveredHour]) / 100), capacity)} · ${
                    currentBaseline[hoveredHour] >= surgeThreshold
                      ? t.tools.forecastSurgeRate(fmtInt(suggestedPeakRate))
                      : t.tools.forecastRate(fmtInt(baseRate))
                  }`}
                </span>
              </div>
            )}

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

          {/* Weekly Profile & LightGBM 8-Feature Matrix */}
          <div className={styles.chartCard}>
            <div className={styles.chartHeader}>
              <h3 className={styles.chartTitle}>
                <Database size={16} aria-hidden />
                <span>{t.tools.weeklyProfileTitle}</span>
              </h3>
              {pipelineData && (
                <span className={styles.chartBaselineBadge}>{t.tools.backendSyncedBadge}</span>
              )}
            </div>
            <div className={styles.weeklyGrid}>
              {weeklyProfile.map((w) => (
                <button
                  key={w.day}
                  type="button"
                  className={`${styles.weeklyCard} ${w.day === dayOfWeek ? styles.weeklyCardActive : ''}`}
                  onClick={() => {
                    setDayOfWeek(w.day);
                    if (pipelineData) void runBackendPipeline(w.day, lotId);
                  }}
                >
                  <span className={styles.weeklyDayLabel}>{t.tools.dayNames[w.day]}</span>
                  <strong className={styles.weeklyDayVal}>{`${w.avg.toFixed(1)}%`}</strong>
                </button>
              ))}
            </div>

            <div className={styles.featureMatrixHeader}>
              <strong className={styles.featureMatrixTitle}>{t.tools.featureMatrixTitle}</strong>
              <p className={styles.featureMatrixSub}>{t.tools.featureMatrixSub}</p>
            </div>
            <div className={table.wrap}>
              <table aria-label={t.tools.featureMatrixTitle} className={table.table}>
                <thead>
                  <tr>
                    <th scope="col" className={table.num}>day_of_week</th>
                    <th scope="col" className={table.num}>hour_of_day</th>
                    <th scope="col" className={table.num}>is_weekend</th>
                    <th scope="col" className={table.num}>total_slots</th>
                    <th scope="col" className={table.num}>hour_sin</th>
                    <th scope="col" className={table.num}>hour_cos</th>
                    <th scope="col" className={table.num}>dow_sin</th>
                    <th scope="col" className={table.num}>dow_cos</th>
                    <th scope="col" className={table.num}>y (occ_pct)</th>
                  </tr>
                </thead>
                <tbody>
                  {computedFeatureRows.map((row) => (
                    <tr key={row.hour_of_day}>
                      <td className={table.num}>{row.day_of_week}</td>
                      <td className={table.num}>{`${row.hour_of_day}:00`}</td>
                      <td className={table.num}>{row.is_weekend}</td>
                      <td className={table.num}>{row.total_slots}</td>
                      <td className={table.num}>{row.hour_sin.toFixed(4)}</td>
                      <td className={table.num}>{row.hour_cos.toFixed(4)}</td>
                      <td className={table.num}>{row.dow_sin.toFixed(4)}</td>
                      <td className={table.num}>{row.dow_cos.toFixed(4)}</td>
                      <td className={`${table.num} ${styles.occStrongCell}`}>{`${row.occupancy_pct}%`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* ADR-0008 Gate Safety Modal */}
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
