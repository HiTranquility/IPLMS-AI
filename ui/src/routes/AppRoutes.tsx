import { AuthenticatedGuard } from '@/components/common/Guard/AuthenticatedGuard';
import { AuthenticatedRoutes } from './AuthenticatedRoutes';

export function AppRoutes() {
  return <AuthenticatedGuard>{(me) => <AuthenticatedRoutes me={me} />}</AuthenticatedGuard>;
}

export default AppRoutes;
