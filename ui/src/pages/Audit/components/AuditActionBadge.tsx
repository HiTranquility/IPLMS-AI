import {
  Bot, Database, FlaskConical, Key, Lock, LogOut, Rocket, Shield, ShieldAlert, ShieldCheck, Tag, UserMinus, UserPlus, Users,
} from 'lucide-react';
import type { ReactNode } from 'react';
import { useI18n } from '@/i18n/I18nProvider';
import type { Messages } from '@/i18n/vi';
import AUDIT_ACTION_CODES from '../auditActionCodes.json';
import styles from './AuditActionBadge.module.css';

/** Nhóm của bộ lọc trang Nhật ký. Mã nào server ghi đều phải có nhóm (test_console_audit_codes.py). */
export type AuditCategory = 'rbac' | 'ml' | 'auth' | 'review' | 'other';

export interface ActionMeta {
  /** Mã gốc trước dấu `:` (vd `role.grant`), hoặc mã thô nếu không có trong từ điển. */
  code: string;
  /** Phần sau dấu `:` (vd tên vai, kết luận chấm), rỗng nếu không có. */
  detail: string;
  category: AuditCategory;
  styleClass: string;
  icon: ReactNode;
}

/** Từ điển mã hành động: khoá là mã server ghi trong `_audit(...)`, khớp theo tiền tố trước `:`. */
const CODE_CATEGORY = AUDIT_ACTION_CODES as Record<string, Exclude<AuditCategory, 'other'>>;

const CODE_STYLE: Record<string, { styleClass: string; icon: ReactNode }> = {
  'member.invite': { styleClass: styles.info, icon: <UserPlus size={12} aria-hidden /> },
  'role.grant': { styleClass: styles.success, icon: <Users size={12} aria-hidden /> },
  'role.revoke': { styleClass: styles.danger, icon: <UserMinus size={12} aria-hidden /> },
  'system.bootstrap_admin': { styleClass: styles.warning, icon: <ShieldCheck size={12} aria-hidden /> },
  'auth.password_locked': { styleClass: styles.danger, icon: <Lock size={12} aria-hidden /> },
  'auth.totp_locked': { styleClass: styles.danger, icon: <Lock size={12} aria-hidden /> },
  'auth.logout': { styleClass: styles.neutral, icon: <LogOut size={12} aria-hidden /> },
  'snapshot.freeze': { styleClass: styles.warning, icon: <Lock size={12} aria-hidden /> },
  'model.promote': { styleClass: styles.purple, icon: <Rocket size={12} aria-hidden /> },
  'model.propose': { styleClass: styles.info, icon: <Rocket size={12} aria-hidden /> },
  'model.retire': { styleClass: styles.neutral, icon: <Rocket size={12} aria-hidden /> },
  'eval.start': { styleClass: styles.info, icon: <FlaskConical size={12} aria-hidden /> },
  'policy.propose': { styleClass: styles.warning, icon: <ShieldAlert size={12} aria-hidden /> },
  'policy.approved': { styleClass: styles.success, icon: <Shield size={12} aria-hidden /> },
  'policy.rejected': { styleClass: styles.danger, icon: <Shield size={12} aria-hidden /> },
};

const CATEGORY_STYLE: Record<AuditCategory, { styleClass: string; icon: ReactNode }> = {
  rbac: { styleClass: styles.info, icon: <Users size={12} aria-hidden /> },
  ml: { styleClass: styles.purple, icon: <Database size={12} aria-hidden /> },
  auth: { styleClass: styles.neutral, icon: <Key size={12} aria-hidden /> },
  review: { styleClass: styles.success, icon: <Tag size={12} aria-hidden /> },
  other: { styleClass: styles.neutral, icon: <Bot size={12} aria-hidden /> },
};

export const AUDIT_CODES = Object.keys(CODE_CATEGORY);

export function getActionMeta(action: string): ActionMeta {
  const sep = action.indexOf(':');
  const base = sep === -1 ? action : action.slice(0, sep);
  const detail = sep === -1 ? '' : action.slice(sep + 1);
  const category = CODE_CATEGORY[base];
  if (!category) return { code: action, detail: '', category: 'other', ...CATEGORY_STYLE.other };
  return { code: base, detail, category, ...(CODE_STYLE[base] ?? CATEGORY_STYLE[category]) };
}

/** Nhãn theo ngôn ngữ đang chọn; mã lạ thì hiện mã thô để không giấu sự kiện. */
export function actionLabel(action: string, t: Messages): string {
  const meta = getActionMeta(action);
  const label = t.audit.actions[meta.code];
  if (!label) return action;
  return meta.detail ? `${label} · ${meta.detail}` : label;
}

export interface AuditActionBadgeProps {
  action: string;
}

export function AuditActionBadge({ action }: AuditActionBadgeProps) {
  const { t } = useI18n();
  const meta = getActionMeta(action);

  return (
    <span className={`${styles.badge} ${meta.styleClass}`} title={action}>
      {meta.icon}
      <span>{actionLabel(action, t)}</span>
    </span>
  );
}

export default AuditActionBadge;
