import {
  Boxes, ClipboardCheck, Database, FlaskConical, Gauge, MessagesSquare, ScanEye, ScrollText, Tags, Users,
  type LucideIcon,
} from 'lucide-react';
import type { Permission } from '@/api/types';

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Hiện khi vai trò có MỘT trong các quyền này; backend vẫn kiểm lại mọi request. */
  permissions: Permission[];
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Copilot',
    items: [
      { to: '/', label: 'Tổng quan', icon: Gauge, permissions: ['ai:metrics:read'] },
      { to: '/copilot', label: 'Copilot Lab', icon: MessagesSquare, permissions: ['ai:chatlog:read'] },
      { to: '/tools', label: 'Công cụ thử', icon: FlaskConical, permissions: ['ai:metrics:read', 'ai:prompt:edit'] },
    ],
  },
  {
    label: 'Vision',
    items: [
      { to: '/vision', label: 'Tổng quan Vision', icon: ScanEye, permissions: ['ai:metrics:read'] },
      { to: '/vision/label', label: 'Gán nhãn', icon: Tags, permissions: ['ai:task:label'] },
      { to: '/vision/review', label: 'Duyệt nhãn', icon: ClipboardCheck, permissions: ['ai:label:approve'] },
      { to: '/vision/datasets', label: 'Dataset & golden', icon: Database, permissions: ['ai:dataset:snapshot', 'ai:model:evaluate'] },
      { to: '/vision/models', label: 'Model & lượt đo', icon: Boxes, permissions: ['ai:metrics:read'] },
    ],
  },
  {
    label: 'Quản trị',
    items: [
      { to: '/members', label: 'Thành viên', icon: Users, permissions: ['ai:member:manage'] },
      { to: '/audit', label: 'Nhật ký', icon: ScrollText, permissions: ['ai:audit:read'] },
    ],
  },
];

export const NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((group) => group.items);

export const allowed = (item: Pick<NavItem, 'permissions'>, granted: Permission[]) =>
  item.permissions.some((p) => granted.includes(p));

