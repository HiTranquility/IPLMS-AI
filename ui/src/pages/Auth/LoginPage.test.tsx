import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { fail, mockApi, ok, renderWithProviders } from '@/test/utils';
import { LoginPage } from './LoginPage';

/** Console chạy dưới `/console` (main.tsx đặt basename); router chỉ thấy phần sau basename. */
function submitAt(browserPath: string, routerPath: string) {
  window.history.replaceState(null, '', browserPath);
  mockApi((url) => (url.endsWith('/auth/password') ? ok({ mfa_required: true }) : fail(401, 'UNAUTHENTICATED')));
  renderWithProviders(<LoginPage />, routerPath);
  fireEvent.change(screen.getByLabelText('Tài khoản quản trị viên'), { target: { value: 'a@x.vn' } });
  fireEvent.change(screen.getByLabelText('Mật khẩu bảo vệ'), { target: { value: 'mat-khau-du-dai' } });
  fireEvent.click(screen.getByRole('button', { name: 'Xác thực & Tiếp tục' }));
}

describe('LoginPage — trang quay lại sau đăng nhập (bug-033)', () => {
  afterEach(() => {
    sessionStorage.clear();
    window.history.replaceState(null, '', '/');
  });

  it('đăng nhập từ gốc /console/ thì không lưu trang quay lại (tránh /console/console/)', async () => {
    submitAt('/console/', '/');
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalled());
    expect(sessionStorage.getItem('console_return_to')).toBeNull();
  });

  it('đăng nhập từ trang con lưu đường dẫn theo router, không kèm basename', async () => {
    submitAt('/console/settings?tab=sessions', '/settings?tab=sessions');
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalled());
    expect(sessionStorage.getItem('console_return_to')).toBe('/settings?tab=sessions');
  });
});
