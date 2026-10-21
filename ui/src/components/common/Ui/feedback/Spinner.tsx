// Chép từ frontend@b4eaa5c packages/shared/src/components/Ui/feedback/Spinner.tsx.
import styles from './Spinner.module.css';

export function Spinner({ size = 20 }: { size?: number }) {
  return <span className={styles.spinner} style={{ width: size, height: size }} aria-hidden />;
}
