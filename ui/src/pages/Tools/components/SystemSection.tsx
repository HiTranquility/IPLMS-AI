import { CheckCircle2, CircleSlash } from 'lucide-react';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { useSystemCheck } from '@/hooks/queries/useToolQueries';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtInt } from '@/utils/format';
import styles from '../ToolsPage.module.css';

export function SystemSection() {
  const { t } = useI18n();
  const check = useSystemCheck();

  return (
    <section className={styles.panel} aria-labelledby="system-title">
      <h2 id="system-title" className={styles.title}>{t.tools.systemTitle}</h2>
      <p className={styles.note}>{t.tools.systemNote}</p>
      {check.isPending && <Loading />}
      {check.error && <ErrorBlock error={check.error} onRetry={() => void check.refetch()} />}
      {check.data && (
        <>
          <ul className={styles.checks}>
            {check.data.checks.map((c) => (
              <li key={c.key} className={styles.check}>
                <div className={styles.checkInfo}>
                  {c.ok ? (
                    <CheckCircle2 size={16} className={styles.ok} aria-hidden />
                  ) : (
                    <CircleSlash size={16} className={styles.missing} aria-hidden />
                  )}
                  <span>{t.tools.checks[c.key] ?? c.label}</span>
                </div>
                <span style={{ fontSize: '11px', color: c.ok ? 'var(--color-success)' : 'var(--color-muted)' }}>
                  {c.ok ? t.tools.configured : t.tools.notConfigured}
                </span>
              </li>
            ))}
          </ul>
          <p className={styles.note}>
            {t.tools.llmModel} <span className={styles.mono}>{check.data.llm_model}</span> ·{' '}
            {t.tools.telemetry(check.data.telemetry_enabled, fmtInt(check.data.telemetry_retention_days))} ·{' '}
            {t.tools.a2Retention(fmtInt(check.data.vision_retention_days))} · {t.tools.visionDevice} <span className={styles.mono}>{check.data.vision_device}</span>
          </p>
        </>
      )}
    </section>
  );
}

export default SystemSection;
