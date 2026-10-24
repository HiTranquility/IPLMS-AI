import { Camera, CheckCircle2, Percent, Sliders } from 'lucide-react';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import table from '@/components/common/Ui/data-display/table.module.css';
import { ThresholdCurve } from '@/components/common/Ui/data-display/ThresholdCurve';
import { useI18n } from '@/i18n/I18nProvider';
import type { Messages } from '@/i18n/vi';
import { MemberStatCard } from '@/pages/Members/components/MemberStatCard';
import type { AccuracyReport } from '@/types/vision';
import { DASH, fmtInt, fmtPercent } from '@/utils/format';
import styles from '../VisionOverviewPage.module.css';

const SHOWN_THRESHOLDS = new Set([0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99]);

function suggestionReason(report: AccuracyReport, t: Messages): string {
  const target = fmtPercent(report.target);
  if (report.total < report.min_samples) return t.visionOverview.reasonFew(report.min_samples, report.total);
  if (report.suggested_threshold === null) return t.visionOverview.reasonNone(target, report.min_samples);
  return t.visionOverview.reasonOk(target, report.min_samples);
}

export interface AccuracySectionProps {
  report: AccuracyReport;
}

export function AccuracySection({ report }: AccuracySectionProps) {
  const { t } = useI18n();

  const suggestedPoint = report.suggested_threshold !== null
    ? report.curve.find((p) => p.threshold === report.suggested_threshold)
    : null;

  const rows = report.curve.filter(
    (p) => SHOWN_THRESHOLDS.has(p.threshold) || p.threshold === report.suggested_threshold,
  );

  return (
    <div className={styles.accuracyWrap}>
      {/* 4 Thẻ KPI ANPR */}
      <div className={styles.kpiGrid}>
        <MemberStatCard
          icon={<CheckCircle2 size={22} />}
          label={t.visionOverview.machineAccuracy}
          value={fmtPercent(report.accuracy)}
          tone="success"
          subtext={
            report.interval_95
              ? t.visionOverview.interval(fmtPercent(report.interval_95[0]), fmtPercent(report.interval_95[1]))
              : t.visionOverview.noSamples
          }
        />
        <MemberStatCard
          icon={<Camera size={22} />}
          label={t.visionOverview.auditSamples}
          value={fmtInt(report.total)}
          tone="primary"
          subtext={t.visionOverview.sources(fmtInt(report.truth_sources.console), fmtInt(report.truth_sources.moderator))}
        />
        <MemberStatCard
          icon={<Sliders size={22} />}
          label={t.visionOverview.suggested}
          value={report.suggested_threshold?.toFixed(2) ?? DASH}
          tone="accent"
          subtext={suggestionReason(report, t)}
        />
        <MemberStatCard
          icon={<Percent size={22} />}
          label={t.visionOverview.autoAccepted}
          value={suggestedPoint ? fmtPercent(suggestedPoint.coverage) : DASH}
          tone="warning"
          subtext={suggestedPoint ? t.visionOverview.autoAcceptedSub(fmtPercent(suggestedPoint.accuracy)) : t.visionOverview.undetermined}
        />
      </div>

      {/* Biểu đồ đường cong Threshold */}
      {report.total > 0 && (
        <div className={styles.chartCard}>
          <div className={styles.chartCardHeader}>
            <div>
              <h3 className={styles.chartCardTitle}>{t.visionOverview.curveTitle}</h3>
              <p className={styles.chartCardSubtitle}>
                {t.visionOverview.curveSubtitle}
              </p>
            </div>
          </div>

          <ThresholdCurve curve={report.curve} suggested={report.suggested_threshold} target={report.target} />
        </div>
      )}

      {/* Bảng phân tích chi tiết các điểm ngưỡng */}
      {report.total > 0 && (
        <div className={styles.tableCard}>
          <div className={styles.tableCardHeader}>
            <h4 className={styles.tableCardTitle}>{t.visionOverview.pointsTitle}</h4>
          </div>
          <div className={table.wrap}>
            <table className={table.table}>
              <thead>
                <tr>
                  <th scope="col" className={table.num}>{t.visionOverview.threshold}</th>
                  <th scope="col" className={table.num}>{t.visionOverview.aboveThreshold}</th>
                  <th scope="col" className={table.num}>{t.visionOverview.correct}</th>
                  <th scope="col" className={table.num}>{t.visionOverview.autoAccepted}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => {
                  const isSuggested = p.threshold === report.suggested_threshold;
                  return (
                    <tr key={p.threshold} style={isSuggested ? { background: 'var(--color-accent-soft)', fontWeight: 600 } : undefined}>
                      <td className={table.num}>
                        {p.threshold.toFixed(2)} {isSuggested && <Badge tone="accent">{t.visionOverview.suggestedBadge}</Badge>}
                      </td>
                      <td className={table.num}>{fmtInt(p.total)}</td>
                      <td className={table.num} style={{ color: p.accuracy && p.accuracy >= report.target ? 'var(--color-success)' : undefined }}>
                        {fmtPercent(p.accuracy)}
                      </td>
                      <td className={table.num}>
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                          <span>{fmtPercent(p.coverage)}</span>
                          {p.coverage !== null && (
                            <span
                              style={{
                                display: 'inline-block',
                                width: 36,
                                height: 4,
                                background: 'var(--color-surface-2)',
                                borderRadius: 2,
                                overflow: 'hidden',
                              }}
                            >
                              <span
                                style={{
                                  display: 'block',
                                  width: `${p.coverage * 100}%`,
                                  height: '100%',
                                  background: 'var(--color-accent)',
                                }}
                              />
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default AccuracySection;
