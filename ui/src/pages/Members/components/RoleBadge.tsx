import { X } from 'lucide-react';
import type { ReactNode } from 'react';
import { useI18n } from '@/i18n/I18nProvider';
import type { Messages } from '@/i18n/vi';
import styles from './RoleBadge.module.css';

export interface RoleMeta {
  role: string;
  cleanName: string;
  label: string;
  className: string;
}

type RoleNames = Messages['members']['roleNames'];

export const ROLE_STYLES: Record<keyof RoleNames, string> = {
  ai_lead: styles.lead,
  ai_console_admin: styles.admin,
  ai_ml_engineer: styles.ml,
  ai_reviewer: styles.reviewer,
  ai_annotator: styles.annotator,
  ai_data_engineer: styles.data,
  ai_analyst: styles.analyst,
};

/** Nhãn vai lấy từ i18n (`members.roleNames`); vai lạ hiện tên kỹ thuật. */
export function getRoleMeta(rawRole: string, names: RoleNames): RoleMeta {
  const cleanName = rawRole.replace(/^ai_/, '');
  const key = (rawRole in ROLE_STYLES ? rawRole : `ai_${cleanName}`) as keyof RoleNames;
  return {
    role: rawRole,
    cleanName,
    label: names[key] ?? cleanName,
    className: ROLE_STYLES[key] ?? styles.analyst,
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

export function RoleBadge({ role, showDesc = false, onRemove, removeTitle, className = '' }: RoleBadgeProps) {
  const { t } = useI18n();
  const meta = getRoleMeta(role, t.members.roleNames);
  const removeLabel = removeTitle ?? t.members.revokeRole;

  return (
    <span
      className={`${styles.badge} ${meta.className} ${className}`}
      title={`${meta.cleanName} — ${meta.label}`}
    >
      <span>{meta.cleanName}</span>
      {showDesc && <span style={{ opacity: 0.75, fontSize: '10px' }}>({meta.label})</span>}
      {onRemove && (
        <button
          type="button"
          className={styles.removeBtn}
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          aria-label={`${removeLabel} ${meta.cleanName}`}
          title={`${removeLabel} ${meta.cleanName}`}
        >
          <X size={11} aria-hidden />
        </button>
      )}
    </span>
  );
}

export default RoleBadge;
