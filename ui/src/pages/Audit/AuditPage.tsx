import { ScrollText } from 'lucide-react';
import table from '@/components/common/Ui/data-display/table.module.css';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { PageHeader } from '@/components/layout/PageHeader';
import { useAudit } from '@/hooks/useConsole';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtDateTime } from '@/utils/format';

export function AuditPage() {
  const { t } = useI18n();
  const audit = useAudit();

  return (
    <>
      <PageHeader
        title={t.audit.title}
        description={t.audit.desc}
      />
      {audit.isPending && <Loading />}
      {audit.error && <ErrorBlock error={audit.error} onRetry={() => void audit.refetch()} />}
      {audit.data?.length === 0 && <EmptyState icon={<ScrollText size={28} />} title={t.audit.empty} />}
      {audit.data && audit.data.length > 0 && (
        <div className={table.wrap}>
          <table className={table.table}>
            <thead>
              <tr>
                <th scope="col">{t.common.at}</th>
                <th scope="col">{t.audit.action}</th>
                <th scope="col">{t.audit.target}</th>
                <th scope="col">{t.audit.actor}</th>
                <th scope="col">{t.common.reason}</th>
              </tr>
            </thead>
            <tbody>
              {audit.data.map((e) => (
                <tr key={e.id}>
                  <td className={table.num}>{fmtDateTime(e.at)}</td>
                  <td className={table.mono}>{e.action}</td>
                  <td className={table.mono}>{e.target_type}:{e.target_id || '—'}</td>
                  <td className={table.mono}>{e.actor_id || t.audit.system}</td>
                  <td>{e.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
