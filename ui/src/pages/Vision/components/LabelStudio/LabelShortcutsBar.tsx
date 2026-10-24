import { useI18n } from '@/i18n/I18nProvider';
import styles from './LabelStudio.module.css';

export function LabelShortcutsBar() {
  const { t } = useI18n();
  const s = t.label.studio;
  return (
    <footer className={styles.dockedShortcuts} role="toolbar" aria-label={s.shortcutsLabel}>
      <span className={styles.dockItem}>
        <kbd className={styles.kbd}>1</kbd> {s.keyCorrect}
      </span>
      <span>·</span>
      <span className={styles.dockItem}>
        <kbd className={styles.kbd}>2</kbd> {s.keyFix}
      </span>
      <span>·</span>
      <span className={styles.dockItem}>
        <kbd className={styles.kbd}>3</kbd> {s.keyUnusable}
      </span>
      <span>·</span>
      <span className={styles.dockItem}>
        <kbd className={styles.kbd}>I</kbd> {s.keyInvert}
      </span>
      <span>·</span>
      <span className={styles.dockItem}>
        <kbd className={styles.kbd}>C</kbd> {s.keyContrast}
      </span>
      <span>·</span>
      <span className={styles.dockItem}>
        <kbd className={styles.kbd}>+/-</kbd> {s.keyZoom}
      </span>
      <span>·</span>
      <span className={styles.dockItem}>
        <kbd className={styles.kbd}>0</kbd> {s.keyReset}
      </span>
    </footer>
  );
}

export default LabelShortcutsBar;
