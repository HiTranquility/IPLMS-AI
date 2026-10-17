import type { BadgeTone } from '@/components/common/Ui/data-display/Badge';
import type { AcceptPolicy, LabelVerdict, ModelStage } from '@/api/types';

export const VERDICT_LABEL: Record<LabelVerdict, string> = {
  CORRECT: 'Biển đúng',
  CORRECTED: 'Sửa biển',
  UNUSABLE: 'Ảnh hỏng',
};

export const REASON_LABEL: Record<string, string> = {
  human_correction: 'Nhân viên sửa ở cổng',
  low_confidence: 'Máy kém tự tin',
  random_audit: 'Bốc kiểm ngẫu nhiên',
  quality_edge_case: 'Ảnh chất lượng biên',
  invalid_image: 'Ảnh lỗi',
};

export const STAGE_LABEL: Record<ModelStage, string> = {
  candidate: 'Ứng viên',
  proposed: 'Chờ duyệt',
  production: 'Đang chạy',
  retired: 'Đã thay',
};

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

export const POLICY_LABEL: Record<AcceptPolicy['status'], string> = {
  PROPOSED: 'Chờ duyệt',
  APPROVED: 'Đã duyệt',
  REJECTED: 'Từ chối',
};
