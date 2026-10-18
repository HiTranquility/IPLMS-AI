import type { BadgeTone } from '@/components/common/Ui/data-display/Badge';
import type { AcceptPolicy, ModelStage } from '@/api/types';

// Nhãn chữ nằm ở từ điển (`t.vision.*`); ở đây chỉ còn tông màu.
export const STAGE_TONE: Record<ModelStage, BadgeTone> = {
  candidate: 'neutral',
  proposed: 'warning',
  production: 'success',
  retired: 'neutral',
};

export const POLICY_TONE: Record<AcceptPolicy['status'], BadgeTone> = {
  PROPOSED: 'warning',
  APPROVED: 'success',
  REJECTED: 'danger',
};
