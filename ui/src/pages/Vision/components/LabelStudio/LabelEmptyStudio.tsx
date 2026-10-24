import { CheckCircle2, FileText, Keyboard, Sparkles } from 'lucide-react';
import { Button } from '@/components/common/Ui/button/Button';
import { useSeedDemoBatch } from '@/hooks/mutations/useVisionMutations';
import { useI18n } from '@/i18n/I18nProvider';
import styles from './LabelStudio.module.css';

interface LabelEmptyStudioProps {
  onSeeded?: () => void;
}

export function LabelEmptyStudio({ onSeeded }: LabelEmptyStudioProps) {
  const { t } = useI18n();
  const e = t.label.empty;
  const s = t.label.studio;
  const seedMutation = useSeedDemoBatch();

  const handleSeed = () => {
    seedMutation.mutate(undefined, {
      onSuccess: () => {
        onSeeded?.();
      },
    });
  };

  const demoPlates = [
    { plate: '51A-888.88', type: e.typeCar, conf: '97%' },
    { plate: '29-B1 999.99', type: e.typeMoto, conf: '88%' },
    { plate: '30E-123.45', type: e.typeTaxi, conf: '93%' },
    { plate: '60-A 888.88', type: e.typeEv, conf: '95%' },
    { plate: '43A-567.89', type: e.typeBlurry, conf: '64%' },
  ];

  return (
    <section className={styles.emptyStudio} aria-label={e.region}>
      <div className={styles.emptyHero}>
        <div className={styles.emptyIconCircle}>
          <CheckCircle2 size={28} aria-hidden />
        </div>
        <h2 className={styles.emptyTitle}>{e.title}</h2>
        <p className={styles.emptyDesc}>
          {e.desc}
        </p>
      </div>

      {/* Lô mẫu thực hành 5 biển số */}
      <div className={styles.seedBatchCard}>
        <div className={styles.seedBatchHeader}>
          <div className={styles.seedBatchTitle}>
            <Sparkles size={16} aria-hidden />
            {e.batchTitle}
          </div>
          <Button
            variant="accent"
            size="md"
            loading={seedMutation.isPending}
            onClick={handleSeed}
            title={e.seedTitle}
          >
            <Sparkles size={14} aria-hidden />
            {e.seed}
          </Button>
        </div>

        <div className={styles.seedPlateGrid}>
          {demoPlates.map((item) => (
            <div key={item.plate} className={styles.seedPlateCard}>
              <span className={styles.seedPlatePlate}>{item.plate}</span>
              <span className={styles.seedPlateMeta}>{item.type}</span>
              <span className={styles.seedPlateMeta}>{e.machineConf(item.conf)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 2 Cột: Quy chuẩn gán nhãn (SOP) & Phím tắt */}
      <div className={styles.emptySplitGrid}>
        <div className={styles.infoCard}>
          <div className={styles.infoCardTitle}>
            <FileText size={16} aria-hidden />
            {e.sopTitle}
          </div>
          <ul className={styles.sopList}>
            <li>
              <strong>{e.sopTwoLineTitle}</strong> {e.sopTwoLine}
            </li>
            <li>
              <strong>{e.sopUnusableTitle}</strong> {e.sopUnusable}
            </li>
            <li>
              <strong>{e.sopFourEyesTitle}</strong> {e.sopFourEyes}
            </li>
          </ul>
        </div>

        <div className={styles.infoCard}>
          <div className={styles.infoCardTitle}>
            <Keyboard size={16} aria-hidden />
            {s.shortcutsLabel}
          </div>
          <div className={styles.shortcutGrid}>
            <div className={styles.shortcutItem}>
              <span>{s.keyCorrect}</span>
              <kbd className={styles.kbd}>1</kbd>
            </div>
            <div className={styles.shortcutItem}>
              <span>{s.keyFix}</span>
              <kbd className={styles.kbd}>2</kbd>
            </div>
            <div className={styles.shortcutItem}>
              <span>{e.shortcutUnusable}</span>
              <kbd className={styles.kbd}>3</kbd>
            </div>
            <div className={styles.shortcutItem}>
              <span>{e.shortcutInvert}</span>
              <kbd className={styles.kbd}>I</kbd>
            </div>
            <div className={styles.shortcutItem}>
              <span>{e.shortcutContrast}</span>
              <kbd className={styles.kbd}>C</kbd>
            </div>
            <div className={styles.shortcutItem}>
              <span>{e.shortcutReset}</span>
              <kbd className={styles.kbd}>0</kbd>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default LabelEmptyStudio;
