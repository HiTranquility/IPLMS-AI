import { Link } from 'react-router-dom';
import { useI18n } from '@/i18n/I18nProvider';
import { EmptyState } from '../Ui/feedback/EmptyState';

export function NotFound() {
  const { t } = useI18n();
  return <EmptyState title={t.app.notFoundTitle} action={<Link to="/">{t.app.backHome}</Link>} />;
}
