import type { TurnFilter } from '@/types/copilot';

/**
 * Type-safe query key factory with hierarchical invalidation support
 * (Theo chuẩn khuôn mẫu `frontend-store/src/constants/queryKeys.ts`).
 */
export const queryKeys = {
  auth: {
    all: () => ['auth'] as const,
    me: () => ['me'] as const,
  },
  copilot: {
    all: () => ['copilot'] as const,
    usage: (days: number) => [...queryKeys.copilot.all(), 'usage', days] as const,
    reviewStatsAll: () => [...queryKeys.copilot.all(), 'review-stats'] as const,
    reviewStats: (days: number) => [...queryKeys.copilot.reviewStatsAll(), days] as const,
    turnsAll: () => [...queryKeys.copilot.all(), 'turns'] as const,
    turns: (filter: TurnFilter) => [...queryKeys.copilot.turnsAll(), filter] as const,
  },
  tools: {
    all: () => ['tools'] as const,
    systemCheck: () => [...queryKeys.tools.all(), 'system'] as const,
    knowledgeDocuments: (lot?: string) => [...queryKeys.tools.all(), 'knowledge', 'documents', lot ?? ''] as const,
    documentChunks: (docId: string, lot?: string, ver?: number) =>
      [...queryKeys.tools.all(), 'knowledge', 'chunks', docId, lot ?? '', ver ?? 0] as const,
  },
  members: {
    all: () => ['members'] as const,
    list: () => [...queryKeys.members.all()] as const,
  },
  audit: {
    all: () => ['audit'] as const,
    list: () => [...queryKeys.audit.all()] as const,
  },
  vision: {
    all: () => ['vision'] as const,
    status: () => [...queryKeys.vision.all(), 'status'] as const,
    labelQueue: () => [...queryKeys.vision.all(), 'queue'] as const,
    reviewQueue: () => [...queryKeys.vision.all(), 'reviews'] as const,
    snapshots: () => [...queryKeys.vision.all(), 'snapshots'] as const,
    models: () => [...queryKeys.vision.all(), 'models'] as const,
    evals: () => [...queryKeys.vision.all(), 'evals'] as const,
    accuracy: () => [...queryKeys.vision.all(), 'accuracy'] as const,
    policies: () => [...queryKeys.vision.all(), 'policies'] as const,
  },
} as const;

export const QUERY_KEYS = {
  AUTH: {
    ME: queryKeys.auth.me,
  },
  COPILOT: {
    ALL: queryKeys.copilot.all,
    USAGE: queryKeys.copilot.usage,
    REVIEW_STATS_ALL: queryKeys.copilot.reviewStatsAll,
    REVIEW_STATS: queryKeys.copilot.reviewStats,
    TURNS_ALL: queryKeys.copilot.turnsAll,
    TURNS: queryKeys.copilot.turns,
  },
  TOOLS: {
    ALL: queryKeys.tools.all,
    SYSTEM_CHECK: queryKeys.tools.systemCheck,
    KNOWLEDGE_DOCUMENTS: queryKeys.tools.knowledgeDocuments,
  },
  MEMBERS: {
    ALL: queryKeys.members.all,
    LIST: queryKeys.members.list,
  },
  AUDIT: {
    ALL: queryKeys.audit.all,
    LIST: queryKeys.audit.list,
  },
  VISION: {
    ALL: queryKeys.vision.all,
    STATUS: queryKeys.vision.status,
    LABEL_QUEUE: queryKeys.vision.labelQueue,
    REVIEW_QUEUE: queryKeys.vision.reviewQueue,
    SNAPSHOTS: queryKeys.vision.snapshots,
    MODELS: queryKeys.vision.models,
    EVALS: queryKeys.vision.evals,
    ACCURACY: queryKeys.vision.accuracy,
    POLICIES: queryKeys.vision.policies,
  },
  // Backwards-compatible flat keys
  ME: queryKeys.auth.me(),
  USAGE: queryKeys.copilot.usage,
  REVIEW_STATS: queryKeys.copilot.reviewStats,
  TURNS: queryKeys.copilot.turns,
  TURNS_ALL: queryKeys.copilot.turnsAll(),
  REVIEW_STATS_ALL: queryKeys.copilot.reviewStatsAll(),
  SYSTEM_CHECK: queryKeys.tools.systemCheck(),
  VISION_STATUS: queryKeys.vision.status(),
  LABEL_QUEUE: queryKeys.vision.labelQueue(),
  REVIEW_QUEUE: queryKeys.vision.reviewQueue(),
  SNAPSHOTS: queryKeys.vision.snapshots(),
  MODELS: queryKeys.vision.models(),
  EVALS: queryKeys.vision.evals(),
  ACCURACY: queryKeys.vision.accuracy(),
  POLICIES: queryKeys.vision.policies(),
} as const;
