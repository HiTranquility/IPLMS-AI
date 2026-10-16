import { Lock } from 'lucide-react';
import { EmptyState } from '../Ui/feedback/EmptyState';

export function Forbidden() {
  return (
    <EmptyState
      icon={<Lock size={28} />}
      title="Vai trò của bạn không mở được mục này"
      description="Quyền trong console do quản trị console cấp theo vai trò. Cần thêm quyền thì liên hệ AI Lead hoặc quản trị console."
    />
  );
}
