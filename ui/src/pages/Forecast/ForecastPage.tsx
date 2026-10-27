import { PageHeader } from '@/components/layout/PageHeader';
import { useI18n } from '@/i18n/I18nProvider';
import { ForecastSimulator } from '@/pages/Tools/components/ForecastSimulator/ForecastSimulator';

/** Mục menu riêng cho Forecast (ai bug-041); trước đây chỉ nằm trong một tab của "Công cụ thử". */
export function ForecastPage() {
  const { t } = useI18n();
  return (
    <>
      <PageHeader title={t.nav.forecast} />
      <ForecastSimulator />
    </>
  );
}

export default ForecastPage;
