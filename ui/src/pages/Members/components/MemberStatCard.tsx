import type { ReactNode } from 'react';
import styles from './MemberStatCard.module.css';

export interface MemberStatCardProps {
  icon: ReactNode;
  label: string;
  value: number | string;
  subtext?: string;
  tone?: 'primary' | 'success' | 'warning' | 'accent';
}

export function MemberStatCard({
  icon,
  label,
  value,
  subtext,
  tone = 'primary',
}: MemberStatCardProps) {
  return (
    <div className={`${styles.card} ${styles[tone]}`}>
      <div className={styles.iconWrap} aria-hidden>
        {icon}
      </div>
      <div className={styles.info}>
        <div className={styles.label}>{label}</div>
        <div className={styles.value}>{value}</div>
        {subtext && <div className={styles.subtext}>{subtext}</div>}
      </div>
    </div>
  );
}

export default MemberStatCard;
