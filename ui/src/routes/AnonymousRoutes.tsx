import { Route, Routes } from 'react-router-dom';
import { AnonymousGuard } from '@/components/common/Guard/AnonymousGuard';
import { LoginPage } from '@/pages/Auth/LoginPage';

export function AnonymousRoutes() {
  return (
    <Routes>
      <Route element={<AnonymousGuard redirectTo="/" />}>
        <Route path="*" element={<LoginPage />} />
      </Route>
    </Routes>
  );
}

export default AnonymousRoutes;
