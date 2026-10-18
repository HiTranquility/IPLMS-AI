import type { BadgeTone } from '@/components/common/Ui/data-display/Badge';
import type { TurnStatus, Verdict } from '@/api/types';

// Nhãn chữ nằm ở từ điển (`t.copilot.status`, `t.copilot.verdict`); ở đây chỉ còn tông màu.
export const STATUS_TONE: Record<TurnStatus, BadgeTone> = {
  SUCCESS: 'neutral',
  REFUSED: 'warning',
  NO_CONTEXT: 'warning',
  ERROR: 'danger',
};

export const VERDICT_TONE: Record<Verdict, BadgeTone> = {
  CORRECT: 'success',
  INCORRECT: 'danger',
  UNSAFE: 'danger',
};
