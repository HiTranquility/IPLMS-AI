import styles from './LabelStudio.module.css';

export function LabelShortcutsBar() {
  return (
    <footer className={styles.dockedShortcuts} role="toolbar" aria-label="Phím tắt thao tác nhanh">
      <span className={styles.dockItem}>
        <kbd className={styles.kbd}>1</kbd> Xác nhận đúng
      </span>
      <span>·</span>
      <span className={styles.dockItem}>
        <kbd className={styles.kbd}>2</kbd> Sửa biển số
      </span>
      <span>·</span>
      <span className={styles.dockItem}>
        <kbd className={styles.kbd}>3</kbd> Ảnh hỏng
      </span>
      <span>·</span>
      <span className={styles.dockItem}>
        <kbd className={styles.kbd}>I</kbd> Đảo màu
      </span>
      <span>·</span>
      <span className={styles.dockItem}>
        <kbd className={styles.kbd}>C</kbd> Tương phản
      </span>
      <span>·</span>
      <span className={styles.dockItem}>
        <kbd className={styles.kbd}>+/-</kbd> Phóng to / Thu nhỏ
      </span>
      <span>·</span>
      <span className={styles.dockItem}>
        <kbd className={styles.kbd}>0</kbd> Reset ảnh
      </span>
    </footer>
  );
}

export default LabelShortcutsBar;
