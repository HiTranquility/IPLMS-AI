import { Check, Plus } from 'lucide-react';
import { useI18n } from '@/i18n/I18nProvider';
import { ROLES } from '@/types/auth';
import { getRoleMeta } from './RoleBadge';
import styles from './RoleSelectorGroup.module.css';

export interface RoleSelectorGroupProps {
  roles?: readonly string[];
  selectedRoles: string[];
  onChange: (roles: string[]) => void;
  disabled?: boolean;
}

export function RoleSelectorGroup({
  roles = ROLES,
  selectedRoles,
  onChange,
  disabled = false,
}: RoleSelectorGroupProps) {
  const { t } = useI18n();
  const toggleRole = (r: string) => {
    if (disabled) return;
    if (selectedRoles.includes(r)) {
      onChange(selectedRoles.filter((item) => item !== r));
    } else {
      onChange([...selectedRoles, r]);
    }
  };

  return (
    <div className={styles.group} role="group" aria-label={t.members.pickRoles}>
      {roles.map((r) => {
        const isSelected = selectedRoles.includes(r);
        const meta = getRoleMeta(r, t.members.roleNames);

        return (
          <button
            key={r}
            type="button"
            className={`${styles.pill} ${isSelected ? styles.pillSelected : ''}`}
            onClick={() => toggleRole(r)}
            disabled={disabled}
            aria-pressed={isSelected}
          >
            <span className={styles.check}>
              {isSelected ? <Check size={13} aria-hidden /> : <Plus size={13} aria-hidden />}
            </span>
            <span className={styles.labelName}>{meta.cleanName}</span>
            <span className={styles.labelDesc}>({meta.label})</span>
          </button>
        );
      })}
    </div>
  );
}

export default RoleSelectorGroup;
