import {
  BookOpen,
  Bot,
  Boxes,
  ClipboardCheck,
  Cpu,
  Database,
  FlaskConical,
  Gauge,
  Layers,
  ScanEye,
  ScrollText,
  ShieldCheck,
  Tags,
  Users,
  type LucideIcon,
} from 'lucide-react';
import type { Permission } from '@/api/types';
import type { Messages } from '@/i18n/vi';
import type { Me } from '@/types/auth';
import type { WorkspacePersona } from '@/types/workspace';

/** Nhãn lấy từ từ điển `nav` theo ngôn ngữ đang dùng. */
type NavLabel = keyof Messages['nav'];

export interface NavItem {
  to: string;
  label: NavLabel;
  icon: LucideIcon;
  /** Hiện khi vai trò có MỘT trong các quyền này; backend vẫn kiểm lại mọi request. */
  permissions: Permission[];
  /** Thuộc các không gian làm việc (persona) nào; nếu không khai báo thì hiện ở mọi persona. */
  personas?: WorkspacePersona[];
}

export interface NavGroup {
  label: NavLabel;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: 'copilot',
    items: [
      { to: '/', label: 'overview', icon: Gauge, permissions: ['ai:metrics:read'], personas: ['analytics'] },
      { to: '/copilot', label: 'copilotLab', icon: Bot, permissions: ['ai:chatlog:read'], personas: ['analytics', 'ml'] },
      { to: '/knowledge', label: 'knowledge', icon: BookOpen, permissions: ['ai:prompt:edit'], personas: ['ml', 'analytics'] },
      { to: '/copilot/logs', label: 'copilotLogs', icon: ScrollText, permissions: ['ai:chatlog:read'], personas: ['analytics'] },
      { to: '/tools', label: 'tools', icon: FlaskConical, permissions: ['ai:metrics:read', 'ai:prompt:edit'], personas: ['ml', 'analytics'] },
    ],
  },
  {
    label: 'vision',
    items: [
      { to: '/vision', label: 'visionOverview', icon: ScanEye, permissions: ['ai:metrics:read'], personas: ['ml'] },
      { to: '/vision/label', label: 'label', icon: Tags, permissions: ['ai:task:label'], personas: ['labeling'] },
      { to: '/vision/review', label: 'review', icon: ClipboardCheck, permissions: ['ai:label:approve'], personas: ['labeling'] },
      { to: '/vision/datasets', label: 'datasets', icon: Database, permissions: ['ai:dataset:snapshot', 'ai:model:evaluate'], personas: ['ml'] },
      { to: '/vision/models', label: 'models', icon: Boxes, permissions: ['ai:metrics:read'], personas: ['ml'] },
    ],
  },
  {
    label: 'admin',
    items: [
      { to: '/members', label: 'members', icon: Users, permissions: ['ai:member:manage'], personas: ['admin'] },
      { to: '/audit', label: 'audit', icon: ScrollText, permissions: ['ai:audit:read'], personas: ['admin'] },
    ],
  },
];

export const NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((group) => group.items);

export const allowed = (
  item: Pick<NavItem, 'permissions'> & { personas?: WorkspacePersona[] },
  granted: Permission[],
  activePersona: WorkspacePersona = 'all',
) => {
  const hasPerm = item.permissions.some((p) => granted.includes(p));
  if (!hasPerm) return false;
  if (activePersona === 'all' || !item.personas) return true;
  return item.personas.includes(activePersona);
};

export interface PersonaMeta {
  id: WorkspacePersona;
  titleKey: 'all' | 'admin' | 'ml' | 'labeling' | 'analytics';
  descKey: 'allDesc' | 'adminDesc' | 'mlDesc' | 'labelingDesc' | 'analyticsDesc';
  icon: LucideIcon;
  badge: string;
  defaultPath: string;
}

export const PERSONA_LIST: PersonaMeta[] = [
  { id: 'all', titleKey: 'all', descKey: 'allDesc', icon: Layers, badge: 'Lead Deck', defaultPath: '/' },
  { id: 'admin', titleKey: 'admin', descKey: 'adminDesc', icon: ShieldCheck, badge: 'Governance', defaultPath: '/members' },
  { id: 'ml', titleKey: 'ml', descKey: 'mlDesc', icon: Cpu, badge: 'ML Studio', defaultPath: '/vision/models' },
  { id: 'labeling', titleKey: 'labeling', descKey: 'labelingDesc', icon: Tags, badge: 'Focus Mode', defaultPath: '/vision/label' },
  { id: 'analytics', titleKey: 'analytics', descKey: 'analyticsDesc', icon: Gauge, badge: 'Copilot Ops', defaultPath: '/' },
];

export function getAvailablePersonas(me: Me): WorkspacePersona[] {
  const isSuper = me.roles.includes('ai_lead') || me.roles.includes('ai_console_admin') || me.roles.length >= 3;
  const list: WorkspacePersona[] = [];

  if (isSuper) {
    list.push('all');
  }

  const canAdmin =
    me.roles.includes('ai_console_admin') ||
    me.roles.includes('ai_lead') ||
    me.permissions.includes('ai:member:manage') ||
    me.permissions.includes('ai:audit:read');
  if (canAdmin) list.push('admin');

  const canMl =
    me.roles.includes('ai_ml_engineer') ||
    me.roles.includes('ai_data_engineer') ||
    me.roles.includes('ai_lead') ||
    me.permissions.includes('ai:model:evaluate');
  if (canMl) list.push('ml');

  const canLabel =
    me.roles.includes('ai_annotator') ||
    me.roles.includes('ai_reviewer') ||
    me.roles.includes('ai_lead') ||
    me.permissions.includes('ai:task:label') ||
    me.permissions.includes('ai:label:approve');
  if (canLabel) list.push('labeling');

  const canAnalytics =
    me.roles.includes('ai_analyst') ||
    me.roles.includes('ai_lead') ||
    me.permissions.includes('ai:metrics:read') ||
    me.permissions.includes('ai:chatlog:read');
  if (canAnalytics) list.push('analytics');

  if (list.length === 0) list.push('all');
  return list;
}
