import {
  Boxes, ClipboardCheck, Database, FlaskConical, Gauge, MessagesSquare, ScanEye, ScrollText, Tags, Users,
  type LucideIcon,
} from 'lucide-react';
import type { Permission } from '@/api/types';
import type { Messages } from '@/i18n/vi';

/** Nhãn lấy từ từ điển `nav` theo ngôn ngữ đang dùng. */
type NavLabel = keyof Messages['nav'];

export interface NavItem {
  to: string;
  label: NavLabel;
  icon: LucideIcon;
  /** Hiện khi vai trò có MỘT trong các quyền này; backend vẫn kiểm lại mọi request. */
  permissions: Permission[];
}

export interface NavGroup {
  label: NavLabel;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: 'copilot',
    items: [
      { to: '/', label: 'overview', icon: Gauge, permissions: ['ai:metrics:read'] },
      { to: '/copilot', label: 'copilotLab', icon: MessagesSquare, permissions: ['ai:chatlog:read'] },
      { to: '/tools', label: 'tools', icon: FlaskConical, permissions: ['ai:metrics:read', 'ai:prompt:edit'] },
    ],
  },
  {
    label: 'vision',
    items: [
      { to: '/vision', label: 'visionOverview', icon: ScanEye, permissions: ['ai:metrics:read'] },
      { to: '/vision/label', label: 'label', icon: Tags, permissions: ['ai:task:label'] },
      { to: '/vision/review', label: 'review', icon: ClipboardCheck, permissions: ['ai:label:approve'] },
      { to: '/vision/datasets', label: 'datasets', icon: Database, permissions: ['ai:dataset:snapshot', 'ai:model:evaluate'] },
      { to: '/vision/models', label: 'models', icon: Boxes, permissions: ['ai:metrics:read'] },
    ],
  },
  {
    label: 'admin',
    items: [
      { to: '/members', label: 'members', icon: Users, permissions: ['ai:member:manage'] },
      { to: '/audit', label: 'audit', icon: ScrollText, permissions: ['ai:audit:read'] },
    ],
  },
];

export const NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((group) => group.items);

export const allowed = (item: Pick<NavItem, 'permissions'>, granted: Permission[]) =>
  item.permissions.some((p) => granted.includes(p));

