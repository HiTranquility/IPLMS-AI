import { PageHeader } from '@/components/layout/PageHeader';
import { useCan } from '@/hooks/common/useCan';
import { useI18n } from '@/i18n/I18nProvider';
import { CopilotSection } from './components/CopilotSection';
import { IngestSection } from './components/IngestSection';
import { SystemSection } from './components/SystemSection';
import styles from './ToolsPage.module.css';

export function ToolsPage() {
  const { t } = useI18n();
  const canTry = useCan('ai:prompt:edit');
  return (
    <>
      <PageHeader
        title={t.tools.title}
        description={t.tools.desc}
      />
      <div className={styles.layout}>
        <SystemSection />
        {canTry && <CopilotSection />}
        {canTry && <IngestSection />}
      </div>
    </>
  );
}

export default ToolsPage;
