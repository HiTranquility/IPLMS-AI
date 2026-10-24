import { useState } from 'react';
import {
  CheckCircle2,
  Cpu,
  Eye,
  GitCommit,
  RefreshCw,
  Type,
} from 'lucide-react';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { useSystemCheck } from '@/hooks/queries/useToolQueries';
import { useI18n } from '@/i18n/I18nProvider';
import styles from './SystemDiagnostics.module.css';

const DASH = '—';

export function SystemDiagnostics() {
  const { t } = useI18n();
  const systemQuery = useSystemCheck();
  const [isRefreshing, setIsRefreshing] = useState(false);

  // /tools/system chỉ báo thiết bị suy luận; YOLO, EasyOCR, PyTorch, CUDA chưa có trường nào
  // nên hiện "—" thay vì hằng số viết cứng (ai bug-018). Server bổ sung trường thì nối vào đây.
  const inferenceDevice = systemQuery.data?.vision_device?.toUpperCase() || DASH;

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await systemQuery.refetch();
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <section className={styles.container} aria-labelledby="diagnostics-heading">
      <div className={styles.header}>
        <div className={styles.headerInfo}>
          <h2 id="diagnostics-heading" className={styles.title}>
            <GitCommit size={18} aria-hidden />
            <span>{t.tools.diagnosticsTitle}</span>
          </h2>
          <p className={styles.desc}>{t.tools.diagnosticsDesc}</p>
        </div>
        <button
          type="button"
          className={styles.refreshBtn}
          onClick={() => void handleRefresh()}
          disabled={isRefreshing}
          aria-label={t.tools.refreshStatus}
        >
          <RefreshCw
            size={14}
            className={isRefreshing ? styles.spinning : undefined}
            aria-hidden
          />
          <span>{t.tools.refreshStatus}</span>
        </button>
      </div>

      {systemQuery.error && <ErrorBlock error={systemQuery.error} onRetry={() => void handleRefresh()} />}
      <p className={styles.desc}>{t.studio.diagnosticsNote}</p>

      {/* Engine Status Cards Grid */}
      <div className={styles.cardsGrid}>
        {/* Card 1: YOLO Plate Detector */}
        <article className={styles.card}>
          <div className={styles.cardTop}>
            <h3 className={styles.cardTitle}>
              <Eye size={16} aria-hidden />
              <span>{t.tools.yoloTitle}</span>
            </h3>
            <span className={styles.badge}>{t.simulated.notReported}</span>
          </div>

          <div className={styles.cardMeta}>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.yoloWeights}</span>
              <span className={styles.metaValue}>{DASH}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.yoloSize}</span>
              <span className={styles.metaValue}>{DASH}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.yoloVersion}</span>
              <span className={styles.metaValue}>{DASH}</span>
            </div>
          </div>
        </article>

        {/* Card 2: EasyOCR Character Reader */}
        <article className={styles.card}>
          <div className={styles.cardTop}>
            <h3 className={styles.cardTitle}>
              <Type size={16} aria-hidden />
              <span>{t.tools.easyOcrTitle}</span>
            </h3>
            <span className={styles.badge}>{t.simulated.notReported}</span>
          </div>

          <div className={styles.cardMeta}>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.ocrLangs}</span>
              <span className={styles.metaValue}>{DASH}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.ocrCacheDir}</span>
              <span className={styles.metaValue}>{DASH}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.ocrStatus}</span>
              <span className={styles.metaValue}>{DASH}</span>
            </div>
          </div>
        </article>

        {/* Card 3: PyTorch & Hardware */}
        <article className={styles.card}>
          <div className={styles.cardTop}>
            <h3 className={styles.cardTitle}>
              <Cpu size={16} aria-hidden />
              <span>{t.tools.pytorchTitle}</span>
            </h3>
            <span className={styles.badge}>{t.simulated.notReported}</span>
          </div>

          <div className={styles.cardMeta}>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.torchVersion}</span>
              <span className={styles.metaValue}>{DASH}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.torchDevice}</span>
              <span className={`${styles.metaValue} ${styles.metaHighlight}`}>
                {inferenceDevice}
              </span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.cudaSupport}</span>
              <span className={styles.metaValue}>{DASH}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.gpuCard}</span>
              <span className={styles.metaValue}>{DASH}</span>
            </div>
          </div>
        </article>
      </div>

      {/* 4 Architectural Conventions Checklist */}
      <div className={styles.conventionsSection}>
        <h3 className={styles.conventionsTitle}>
          <GitCommit size={16} aria-hidden />
          <span>{t.tools.conventionsTitle}</span>
        </h3>

        <div className={styles.conventionsGrid}>
          {/* Convention 1 */}
          <div className={styles.conventionItem}>
            <div className={styles.conventionHeader}>
              <CheckCircle2 size={16} aria-hidden />
              <span>{t.tools.convention1Title}</span>
            </div>
            <p className={styles.conventionDesc}>{t.tools.convention1Desc}</p>
          </div>

          {/* Convention 2 */}
          <div className={styles.conventionItem}>
            <div className={styles.conventionHeader}>
              <CheckCircle2 size={16} aria-hidden />
              <span>{t.tools.convention2Title}</span>
            </div>
            <p className={styles.conventionDesc}>{t.tools.convention2Desc}</p>
          </div>

          {/* Convention 3 */}
          <div className={styles.conventionItem}>
            <div className={styles.conventionHeader}>
              <CheckCircle2 size={16} aria-hidden />
              <span>{t.tools.convention3Title}</span>
            </div>
            <p className={styles.conventionDesc}>{t.tools.convention3Desc}</p>
          </div>

          {/* Convention 4 */}
          <div className={styles.conventionItem}>
            <div className={styles.conventionHeader}>
              <CheckCircle2 size={16} aria-hidden />
              <span>{t.tools.convention4Title}</span>
            </div>
            <p className={styles.conventionDesc}>{t.tools.convention4Desc}</p>
          </div>
        </div>
      </div>
    </section>
  );
}

export default SystemDiagnostics;
