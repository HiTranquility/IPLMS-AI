import { Tags } from 'lucide-react';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { PageHeader } from '@/components/layout/PageHeader';
import { useLabelQueue } from '@/hooks/queries/useVisionQueries';
import { useI18n } from '@/i18n/I18nProvider';
import { LabelForm } from './components/LabelForm';
import styles from './LabelPage.module.css';

export function LabelPage() {
  const { t } = useI18n();
  const queue = useLabelQueue();
  const current = queue.data?.[0];

  return (
    <div className={styles.page}>
      <PageHeader
        title={t.label.title}
        description={t.label.desc}
      />
      {queue.isPending && <Loading />}
      {queue.error && <ErrorBlock error={queue.error} onRetry={() => void queue.refetch()} />}
      {queue.isSuccess && !current && (
        <EmptyState icon={<Tags size={28} />} title={t.label.emptyTitle} description={t.label.emptyDesc} />
      )}
      {current && <LabelForm key={current.capture_id} sample={current} remaining={queue.data!.length} />}
    </div>
  );
}

export default LabelPage;
