import { ScrollText } from 'lucide-react';
import table from '@/components/common/Ui/data-display/Table.module.css';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { PageHeader } from '@/components/layout/PageHeader';
import { useAudit } from '@/hooks/useConsole';
import { fmtDateTime } from '@/utils/format';

export function AuditPage() {
  const audit = useAudit();

  return (
    <>
      <PageHeader
        title="Nhật ký console"
        description="200 sự kiện gần nhất. Bảng chỉ cho thêm mới — trigger trong DB chặn sửa/xoá, nên đây là dấu vết đầy đủ của mọi thay đổi quyền và lần chấm."
      />
      {audit.isPending && <Loading />}
      {audit.error && <ErrorBlock error={audit.error} onRetry={() => void audit.refetch()} />}
      {audit.data?.length === 0 && <EmptyState icon={<ScrollText size={28} />} title="Chưa có sự kiện nào" />}
      {audit.data && audit.data.length > 0 && (
        <div className={table.wrap}>
          <table className={table.table}>
            <thead>
              <tr>
                <th scope="col">Lúc</th>
                <th scope="col">Hành động</th>
                <th scope="col">Đối tượng</th>
                <th scope="col">Người làm</th>
                <th scope="col">Lý do</th>
              </tr>
            </thead>
            <tbody>
              {audit.data.map((e) => (
                <tr key={e.id}>
                  <td className={table.num}>{fmtDateTime(e.at)}</td>
                  <td className={table.mono}>{e.action}</td>
                  <td className={table.mono}>{e.target_type}:{e.target_id || '—'}</td>
                  <td className={table.mono}>{e.actor_id || 'hệ thống'}</td>
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
