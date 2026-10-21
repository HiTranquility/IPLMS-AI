import { Database, Key, Lock, Rocket, Shield, ShieldAlert, UserMinus, UserPlus, Users } from 'lucide-react';
import type { ReactNode } from 'react';
import styles from './AuditActionBadge.module.css';

export interface ActionMeta {
  labelVi: string;
  labelEn: string;
  category: 'rbac' | 'ml' | 'auth' | 'other';
  styleClass: string;
  icon: ReactNode;
}

export const ACTION_METAS: Record<string, ActionMeta> = {
  'ai:member:invited': {
    labelVi: 'Mời thành viên',
    labelEn: 'Member Invited',
    category: 'rbac',
    styleClass: styles.info,
    icon: <UserPlus size={12} aria-hidden />,
  },
  'ai:role:granted': {
    labelVi: 'Cấp vai trò',
    labelEn: 'Role Granted',
    category: 'rbac',
    styleClass: styles.success,
    icon: <Users size={12} aria-hidden />,
  },
  'ai:role:revoked': {
    labelVi: 'Thu hồi vai trò',
    labelEn: 'Role Revoked',
    category: 'rbac',
    styleClass: styles.danger,
    icon: <UserMinus size={12} aria-hidden />,
  },
  'ai:golden:freeze': {
    labelVi: 'Đóng băng Golden',
    labelEn: 'Golden Frozen',
    category: 'ml',
    styleClass: styles.warning,
    icon: <Lock size={12} aria-hidden />,
  },
  'ai:model:promote': {
    labelVi: 'Thăng cấp Model',
    labelEn: 'Model Promoted',
    category: 'ml',
    styleClass: styles.purple,
    icon: <Rocket size={12} aria-hidden />,
  },
  'ai:model:propose': {
    labelVi: 'Đề xuất Model',
    labelEn: 'Model Proposed',
    category: 'ml',
    styleClass: styles.info,
    icon: <Rocket size={12} aria-hidden />,
  },
  'ai:policy:decide': {
    labelVi: 'Duyệt chính sách',
    labelEn: 'Policy Decided',
    category: 'ml',
    styleClass: styles.success,
    icon: <Shield size={12} aria-hidden />,
  },
  'ai:policy:propose': {
    labelVi: 'Đề xuất chính sách',
    labelEn: 'Policy Proposed',
    category: 'ml',
    styleClass: styles.warning,
    icon: <ShieldAlert size={12} aria-hidden />,
  },
  'ai:dataset:snapshot': {
    labelVi: 'Tạo Snapshot Dataset',
    labelEn: 'Dataset Snapshot',
    category: 'ml',
    styleClass: styles.info,
    icon: <Database size={12} aria-hidden />,
  },
  'ai:auth:login': {
    labelVi: 'Đăng nhập',
    labelEn: 'User Login',
    category: 'auth',
    styleClass: styles.neutral,
    icon: <Key size={12} aria-hidden />,
  },
};

export function getActionMeta(action: string): ActionMeta {
  if (ACTION_METAS[action]) return ACTION_METAS[action];

  if (action.includes('role') || action.includes('member')) {
    return {
      labelVi: action.replace(/^ai:/, ''),
      labelEn: action.replace(/^ai:/, ''),
      category: 'rbac',
      styleClass: styles.info,
      icon: <Users size={12} aria-hidden />,
    };
  }
  if (action.includes('model') || action.includes('dataset') || action.includes('golden') || action.includes('policy')) {
    return {
      labelVi: action.replace(/^ai:/, ''),
      labelEn: action.replace(/^ai:/, ''),
      category: 'ml',
      styleClass: styles.purple,
      icon: <Database size={12} aria-hidden />,
    };
  }
  if (action.includes('auth') || action.includes('mfa')) {
    return {
      labelVi: action.replace(/^ai:/, ''),
      labelEn: action.replace(/^ai:/, ''),
      category: 'auth',
      styleClass: styles.neutral,
      icon: <Key size={12} aria-hidden />,
    };
  }

  return {
    labelVi: action.replace(/^ai:/, ''),
    labelEn: action.replace(/^ai:/, ''),
    category: 'other',
    styleClass: styles.neutral,
    icon: <Shield size={12} aria-hidden />,
  };
}

export interface AuditActionBadgeProps {
  action: string;
}

export function AuditActionBadge({ action }: AuditActionBadgeProps) {
  const meta = getActionMeta(action);

  return (
    <span className={`${styles.badge} ${meta.styleClass}`} title={action}>
      {meta.icon}
      <span>{meta.labelVi}</span>
    </span>
  );
}

export default AuditActionBadge;
