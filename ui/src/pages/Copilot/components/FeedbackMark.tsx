import { ThumbsDown, ThumbsUp } from 'lucide-react';
import { useI18n } from '@/i18n/I18nProvider';
import type { Turn } from '@/types/copilot';

export interface FeedbackMarkProps {
  value: Turn['feedback'];
}

export function FeedbackMark({ value }: FeedbackMarkProps) {
  const { t } = useI18n();
  if (value === 1) return <ThumbsUp size={14} aria-label={t.copilot.markedUp} />;
  if (value === -1) return <ThumbsDown size={14} aria-label={t.copilot.markedDown} />;
  return null;
}

export default FeedbackMark;
