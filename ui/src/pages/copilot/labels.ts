import type { BadgeTone } from '@/components/common/Ui/data-display/Badge';
import type { TurnStatus, Verdict } from '@/api/types';

export const STATUS_LABEL: Record<TurnStatus, string> = {
  SUCCESS: 'Đã trả lời',
  REFUSED: 'Guard chặn',
  NO_CONTEXT: 'Thiếu ngữ cảnh',
  ERROR: 'Lỗi',
};

export const STATUS_TONE: Record<TurnStatus, BadgeTone> = {
  SUCCESS: 'neutral',
  REFUSED: 'warning',
  NO_CONTEXT: 'warning',
  ERROR: 'danger',
};

export const VERDICT_LABEL: Record<Verdict, string> = {
  CORRECT: 'Đúng',
  INCORRECT: 'Sai',
  UNSAFE: 'Không an toàn',
};

export const VERDICT_TONE: Record<Verdict, BadgeTone> = {
  CORRECT: 'success',
  INCORRECT: 'danger',
  UNSAFE: 'danger',
};
