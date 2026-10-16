import { Gauge, MessagesSquare, ScrollText, Users, type LucideIcon } from 'lucide-react';
import type { Permission } from '@/api/types';

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  permission: Permission;
}

/** Mục nav chỉ hiện khi vai trò có quyền; backend vẫn kiểm lại mọi request. */
export const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Tổng quan', icon: Gauge, permission: 'ai:metrics:read' },
  { to: '/copilot', label: 'Copilot Lab', icon: MessagesSquare, permission: 'ai:chatlog:read' },
  { to: '/members', label: 'Thành viên', icon: Users, permission: 'ai:member:manage' },
  { to: '/audit', label: 'Nhật ký', icon: ScrollText, permission: 'ai:audit:read' },
];

