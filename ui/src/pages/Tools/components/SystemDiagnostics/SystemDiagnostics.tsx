import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Cpu,
  Eye,
  GitCommit,
  Layers,
  RefreshCw,
  Sliders,
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

  // Số liệu thật từ /tools/system (ai bug-018): server không biết chắc thì null → "—", không hằng số.
  const inferenceDevice = systemQuery.data?.vision_device?.toUpperCase() || DASH;
  const eng = systemQuery.data?.engines;
  const loadedBadge = (loaded: boolean | null | undefined) =>
    loaded == null ? t.simulated.notReported : loaded ? t.studio.engineLoaded : t.studio.engineNotLoaded;
  const yesNo = (value: boolean | null | undefined) => (value == null ? DASH : value ? t.studio.yes : t.studio.no);
  const weightsMb =
    eng?.yolo_weights_bytes != null ? t.studio.megabytes((eng.yolo_weights_bytes / 1024 / 1024).toFixed(1)) : DASH;

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
        <div className={styles.headerActions}>
          <Link to="/settings" className={`${styles.refreshBtn} ${styles.settingsLinkBtn}`}>
            <Sliders size={14} aria-hidden />
            <span>{t.settings.openSettingsBtn}</span>
          </Link>
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
            <span className={styles.badge}>{loadedBadge(eng?.yolo_loaded)}</span>
          </div>

          <div className={styles.cardMeta}>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.yoloWeights}</span>
              <span className={styles.metaValue} title={eng?.yolo_weights_path}>{eng?.yolo_weights_path || DASH}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.yoloSize}</span>
              <span className={styles.metaValue}>{weightsMb}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.yoloVersion}</span>
              <span className={styles.metaValue}>{eng?.yolo_version || DASH}</span>
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
            <span className={styles.badge}>{loadedBadge(eng?.ocr_loaded)}</span>
          </div>

          <div className={styles.cardMeta}>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.ocrLangs}</span>
              <span className={styles.metaValue}>{eng?.ocr_languages.length ? eng.ocr_languages.join(', ') : DASH}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.ocrCacheDir}</span>
              <span className={styles.metaValue} title={eng?.ocr_cache_dir ?? undefined}>{eng?.ocr_cache_dir || DASH}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.ocrStatus}</span>
              <span className={styles.metaValue}>{loadedBadge(eng?.ocr_loaded)}</span>
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
            <span className={styles.badge}>{eng?.torch_version ? t.studio.engineLoaded : t.simulated.notReported}</span>
          </div>

          <div className={styles.cardMeta}>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.torchVersion}</span>
              <span className={styles.metaValue}>{eng?.torch_version || DASH}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.torchDevice}</span>
              <span className={`${styles.metaValue} ${styles.metaHighlight}`}>
                {inferenceDevice}
              </span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.cudaSupport}</span>
              <span className={styles.metaValue}>{yesNo(eng?.cuda_available)}</span>
            </div>
          </div>
        </article>

        {/* Card 4: VRAM Allocation & 4GB Workstation Safe Architecture */}
        <article className={styles.card}>
          <div className={styles.cardTop}>
            <h3 className={styles.cardTitle}>
              <Layers size={16} aria-hidden />
              <span>{t.tools.vramBudgetTitle}</span>
            </h3>
            <span className={`${styles.badge} ${styles.badgeSuccess}`}>4GB SAFE</span>
          </div>

          <div className={styles.cardMeta}>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.vramLlm}</span>
              <span className={`${styles.metaValue} ${styles.metaHighlight}`}>{t.tools.vramLlmLayers}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.vramLlmMem}</span>
              <span className={styles.metaValue}>~2.93 GB VRAM</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.vramVision}</span>
              <span className={styles.metaValue}>{t.tools.vramVisionDevice}</span>
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t.tools.vramHeadroom}</span>
              <span className={styles.metaValue}>{t.tools.vramHeadroomEst}</span>
            </div>
          </div>
        </article>
      </div>
    </section>
  );
}

export default SystemDiagnostics;
