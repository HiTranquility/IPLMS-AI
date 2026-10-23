import { useState } from 'react';
import { Segmented } from '@/components/common/Ui/button/Segmented';
import { PageHeader } from '@/components/layout/PageHeader';
import { useCan } from '@/hooks/common/useCan';
import { useI18n } from '@/i18n/I18nProvider';
import { CopilotSection } from './components/CopilotSection';
import { ForecastSimulator } from './components/ForecastSimulator/ForecastSimulator';
import { IngestSection } from './components/IngestSection';
import { SystemDiagnostics } from './components/SystemDiagnostics/SystemDiagnostics';
import { SystemSection } from './components/SystemSection';
import styles from './ToolsPage.module.css';

type ToolsTab = 'all' | 'diagnostics' | 'forecast' | 'sandbox';

export function ToolsPage() {
  const { t } = useI18n();
  const canTry = useCan('ai:prompt:edit');
  const [activeTab, setActiveTab] = useState<ToolsTab>('all');

  const tabOptions: { value: ToolsTab; label: string }[] = [
    { value: 'all', label: t.tools.tabAll },
    { value: 'diagnostics', label: t.tools.tabDiagnostics },
    { value: 'forecast', label: t.tools.tabForecast },
    { value: 'sandbox', label: t.tools.tabTools },
  ];

  return (
    <>
      <PageHeader
        title={t.tools.title}
        description={t.tools.desc}
      />

      <div className={styles.tabBar}>
        <Segmented
          label={t.tools.title}
          value={activeTab}
          options={tabOptions}
          onChange={(val) => setActiveTab(val)}
        />
      </div>

      <div className={styles.sectionsContainer}>
        {/* System & Engines Diagnostics Inspector */}
        {(activeTab === 'all' || activeTab === 'diagnostics') && (
          <SystemDiagnostics />
        )}

        {/* Forecast & Dynamic Tariff Simulator */}
        {(activeTab === 'all' || activeTab === 'forecast') && (
          <ForecastSimulator />
        )}

        {/* Console Configuration, Copilot & Ingest Sandbox */}
        {(activeTab === 'all' || activeTab === 'sandbox' || activeTab === 'diagnostics') && (
          <div className={styles.layout}>
            {(activeTab === 'all' || activeTab === 'diagnostics') && <SystemSection />}
            {(activeTab === 'all' || activeTab === 'sandbox') && canTry && <CopilotSection />}
            {(activeTab === 'all' || activeTab === 'sandbox') && canTry && <IngestSection />}
          </div>
        )}
      </div>
    </>
  );
}

export default ToolsPage;
