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
  TrendingUp,
  Users,
  type LucideIcon,
} from 'lucide-react';
import type { Permission } from '@/api/types';
import type { Messages } from '@/i18n/vi';
import type { Me, Role } from '@/types/auth';
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
      { to: '/forecast', label: 'forecast', icon: TrendingUp, permissions: ['ai:metrics:read'], personas: ['ml', 'analytics'] },
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

/**
 * Vai → không gian làm việc. Quyền từng mục menu vẫn lấy từ `me.permissions`
 * (ma trận ở `app/core/console/engines/access_policy.py`); bảng này chỉ chia menu theo vai.
 */
export const ROLE_WORKSPACES: Record<Role, WorkspacePersona[]> = {
  ai_console_admin: ['admin'],
  ai_lead: ['admin', 'ml', 'labeling', 'analytics'],
  ai_ml_engineer: ['ml'],
  ai_data_engineer: ['ml'],
  ai_reviewer: ['labeling', 'analytics'],
  ai_annotator: ['labeling'],
  ai_analyst: ['analytics'],
};

export function getAvailablePersonas(me: Me): WorkspacePersona[] {
  const own = new Set(me.roles.flatMap((role) => ROLE_WORKSPACES[role] ?? []));
  const list = PERSONA_LIST.map((p) => p.id).filter((id) => id !== 'all' && own.has(id));
  // Có từ hai không gian trở lên thì thêm "Tất cả"; không có vai nào thì hiện theo quyền.
  return list.length === 1 ? list : ['all', ...list];
}

/** Không gian dùng thật: đã chọn và còn thuộc tài khoản này, nếu không thì không gian đầu tiên của nó. */
export function resolvePersona(me: Me, saved: WorkspacePersona | null): WorkspacePersona {
  const available = getAvailablePersonas(me);
  return saved && available.includes(saved) ? saved : available[0];
}
