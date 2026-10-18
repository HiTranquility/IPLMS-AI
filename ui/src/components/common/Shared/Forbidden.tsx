import { Lock } from 'lucide-react';
import { useI18n } from '@/i18n/I18nProvider';
import { EmptyState } from '../Ui/feedback/EmptyState';

export function Forbidden() {
  const { t } = useI18n();
  return (
    <EmptyState
      icon={<Lock size={28} />}
      title={t.app.forbiddenTitle}
      description={t.app.forbiddenDesc}
    />
  );
}
