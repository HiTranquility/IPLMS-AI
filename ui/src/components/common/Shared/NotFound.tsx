import { Link } from 'react-router-dom';
import { EmptyState } from '../Ui/feedback/EmptyState';

export function NotFound() {
  return <EmptyState title="Không có trang này" action={<Link to="/">Về tổng quan</Link>} />;
}
