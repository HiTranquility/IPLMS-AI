import { useState } from 'react';
import {
  CheckCircle2,
  Cpu,
  Eye,
  GitCommit,
  RefreshCw,
  Type,
} from 'lucide-react';
import { useSystemCheck } from '@/hooks/queries/useToolQueries';
import { useI18n } from '@/i18n/I18nProvider';
import styles from './SystemDiagnostics.module.css';

interface EngineDiagnosticsState {
  yoloPath: string;
  yoloSizeMb: number;
  yoloVersion: string;
  yoloReady: boolean;
  ocrLangs: string[];
  ocrCacheDir: string;
  ocrCached: boolean;
  torchVersion: string;
  inferenceDevice: string;
  cudaAvailable: boolean;
  gpuName: string;
  lastChecked: Date;
}

export function SystemDiagnostics() {
  const { t } = useI18n();
  const systemQuery = useSystemCheck();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  // Default / probed diagnostics values aligned with Khoa's HTML & IPLMS config
  const diagnostics: EngineDiagnosticsState = {
    yoloPath: 'model/artifacts/bootstrap/anpr/best.pt',
    yoloSizeMb: 14.2,
    yoloVersion: 'bootstrap-v1',
    yoloReady: true,
    ocrLangs: ['en', 'vi'],
    ocrCacheDir: 'var/easyocr-cache/',
    ocrCached: true,
    torchVersion: '2.6.0',
    inferenceDevice: systemQuery.data?.vision_device?.toUpperCase() || 'CPU',
    cudaAvailable: false,
    gpuName: 'None',
    lastChecked: lastRefreshed,
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await systemQuery.refetch();
    } finally {
      setTimeout(() => {
        setIsRefreshing(false);
        setLastRefreshed(new Date());
      }, 400);
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

      {/* Engine Status Cards Grid */}
      <div className={styles.cardsGrid}>
        {/* Card 1: YOLO Plate Detector */}
        <article className={styles.card}>
          <div className={styles.cardTop}>
            <h3 className={styles.cardTitle}>
              <Eye size={16} aria-hidden />
              <span>{t.tools.yoloTitle}</span>
            </h3>
            <span
              className={`${styles.badge} ${
                diagnostics.yoloReady ? styles.badgeSuccess : styles.badgeDanger
              }`}
            >
              {diagnostics.yoloReady ? t.tools.statusReady : t.tools.statusMissing}
            </span>
          </div>

          <div className={styles.cardMeta}>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.yoloWeights}</span>
              <span className={styles.metaValue} title={diagnostics.yoloPath}>
                {diagnostics.yoloPath}
              </span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.yoloSize}</span>
              <span className={`${styles.metaValue} ${styles.metaHighlight}`}>
                {diagnostics.yoloSizeMb.toFixed(1)} MB
              </span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.yoloVersion}</span>
              <span className={styles.metaValue}>{diagnostics.yoloVersion}</span>
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
            <span
              className={`${styles.badge} ${
                diagnostics.ocrCached ? styles.badgeInfo : styles.badgeWarning
              }`}
            >
              {diagnostics.ocrCached ? t.tools.statusCached : t.tools.statusUncached}
            </span>
          </div>

          <div className={styles.cardMeta}>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.ocrLangs}</span>
              <span className={`${styles.metaValue} ${styles.metaHighlight}`}>
                {JSON.stringify(diagnostics.ocrLangs)}
              </span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.ocrCacheDir}</span>
              <span className={styles.metaValue} title={diagnostics.ocrCacheDir}>
                {diagnostics.ocrCacheDir}
              </span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.ocrStatus}</span>
              <span className={styles.metaValue}>{t.tools.statusReadyOffline}</span>
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
            <span
              className={`${styles.badge} ${
                diagnostics.cudaAvailable ? styles.badgeSuccess : styles.badgeInfo
              }`}
            >
              {diagnostics.cudaAvailable ? t.tools.statusAccelerated : t.tools.statusStandard}
            </span>
          </div>

          <div className={styles.cardMeta}>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.torchVersion}</span>
              <span className={styles.metaValue}>{diagnostics.torchVersion}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.torchDevice}</span>
              <span className={`${styles.metaValue} ${styles.metaHighlight}`}>
                {diagnostics.inferenceDevice}
              </span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.cudaSupport}</span>
              <span className={styles.metaValue}>
                {diagnostics.cudaAvailable ? t.tools.cudaTrue : t.tools.cudaFalse}
              </span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.gpuCard}</span>
              <span className={styles.metaValue}>
                {diagnostics.gpuName === 'None' ? t.tools.gpuNone : diagnostics.gpuName}
              </span>
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
