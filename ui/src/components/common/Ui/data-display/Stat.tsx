import styles from './Stat.module.css';

interface StatProps {
  label: string;
  value: string;
  hint?: string;
}

/** Một số liệu: nhãn trên, số tabular dưới. Không có dữ liệu thì truyền "—" (Hallmark luật 2). */
export function Stat({ label, value, hint }: StatProps) {
  return (
    <div className={styles.stat}>
      <dt className={styles.label}>{label}</dt>
      <dd className={styles.value}>{value}</dd>
      {hint && <dd className={styles.hint}>{hint}</dd>}
    </div>
  );
}
