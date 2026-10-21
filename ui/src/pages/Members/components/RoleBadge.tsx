import { X } from 'lucide-react';
import type { ReactNode } from 'react';
import styles from './RoleBadge.module.css';

export interface RoleMeta {
  role: string;
  cleanName: string;
  labelVi: string;
  className: string;
}

export const ROLE_DEFINITIONS: Record<string, { labelVi: string; styleClass: string }> = {
  ai_lead: { labelVi: 'Trưởng nhóm', styleClass: styles.lead },
  ai_console_admin: { labelVi: 'Quản trị hệ thống', styleClass: styles.admin },
  ai_ml_engineer: { labelVi: 'Kỹ sư ML', styleClass: styles.ml },
  ai_reviewer: { labelVi: 'Duyệt nhãn', styleClass: styles.reviewer },
  ai_annotator: { labelVi: 'Gán nhãn', styleClass: styles.annotator },
  ai_data_engineer: { labelVi: 'Kỹ sư dữ liệu', styleClass: styles.data },
  ai_analyst: { labelVi: 'Chuyên viên phân tích', styleClass: styles.analyst },
};

export function getRoleMeta(rawRole: string): RoleMeta {
  const cleanName = rawRole.replace(/^ai_/, '');
  const found = ROLE_DEFINITIONS[rawRole] || ROLE_DEFINITIONS[`ai_${cleanName}`] || {
    labelVi: cleanName,
    styleClass: styles.analyst,
  };
  return {
    role: rawRole,
    cleanName,
    labelVi: found.labelVi,
    className: found.styleClass,
  };
}

export interface RoleBadgeProps {
  role: string;
  showDesc?: boolean;
  onRemove?: () => void;
  removeTitle?: string;
  children?: ReactNode;
  className?: string;
}

export function RoleBadge({ role, showDesc = false, onRemove, removeTitle = 'Thu hồi vai trò', className = '' }: RoleBadgeProps) {
  const meta = getRoleMeta(role);

  return (
    <span
      className={`${styles.badge} ${meta.className} ${className}`}
      title={`${meta.cleanName} — ${meta.labelVi}`}
    >
      <span>{meta.cleanName}</span>
      {showDesc && <span style={{ opacity: 0.75, fontSize: '10px' }}>({meta.labelVi})</span>}
      {onRemove && (
        <button
          type="button"
          className={styles.removeBtn}
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          aria-label={`${removeTitle} ${meta.cleanName}`}
          title={`${removeTitle} ${meta.cleanName}`}
        >
          <X size={11} aria-hidden />
        </button>
      )}
    </span>
  );
}

export default RoleBadge;
