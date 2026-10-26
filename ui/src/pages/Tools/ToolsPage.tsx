import { useState } from 'react';
import { Segmented } from '@/components/common/Ui/button/Segmented';
import { PageHeader } from '@/components/layout/PageHeader';
import { useI18n } from '@/i18n/I18nProvider';
import { ForecastSimulator } from './components/ForecastSimulator/ForecastSimulator';
import { SystemDiagnostics } from './components/SystemDiagnostics/SystemDiagnostics';
import { SystemSection } from './components/SystemSection';
import styles from './ToolsPage.module.css';

type ToolsTab = 'all' | 'diagnostics' | 'forecast';

export function ToolsPage() {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<ToolsTab>('all');

  const tabOptions: { value: ToolsTab; label: string }[] = [
    { value: 'all', label: t.tools.tabAll },
    { value: 'diagnostics', label: t.tools.tabDiagnostics },
    { value: 'forecast', label: t.tools.tabForecast },
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
          onChange={(val) => setActiveTab(val as ToolsTab)}
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

        {/* Console Configuration & Access */}
        {(activeTab === 'all' || activeTab === 'diagnostics') && (
          <div className={styles.layout}>
            <SystemSection />
          </div>
        )}
      </div>
    </>
  );
}

export default ToolsPage;
