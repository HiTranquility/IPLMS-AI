import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { fail, me, mockApi, ok, renderWithProviders } from '@/test/utils';
import { App } from './App';

const emptyUsage = {
  window_days: 7, total_requests: 0, success_requests: 0, refused_requests: 0, no_context_requests: 0,
  error_requests: 0, avg_latency_ms: 0, p95_latency_ms: 0, input_tokens: 0, output_tokens: 0,
  cost_known: false, total_cost_usd: 0, avg_cost_usd: 0, thumbs_up: 0, thumbs_down: 0, days: [],
};
const noReviews = { window_days: 7, reviewed: 0, correct: 0, incorrect: 0, unsafe: 0, accuracy: null };

describe('App — cổng phiên và quyền', () => {
  it('chưa đăng nhập thì hiện trang đăng nhập Google', async () => {
    mockApi(() => fail(401, 'UNAUTHENTICATED'));
    renderWithProviders(<App />);
    expect(await screen.findByRole('link', { name: 'Đăng nhập bằng Google' })).toHaveProperty('href', expect.stringContaining('/console/api/auth/google/start'));
  });

  it('chưa qua TOTP thì chỉ hiện bước xác thực, chưa có nav', async () => {
    mockApi((url) => (url.endsWith('/me') ? ok(me({ mfa_done: false, permissions: [] })) : undefined));
    renderWithProviders(<App />);
    expect(await screen.findByRole('heading', { name: 'Nhập mã xác thực' })).toBeTruthy();
    expect(screen.queryByRole('navigation')).toBeNull();
  });

  it('admin khẩn cấp có khoá từ CLI thì nhập mã luôn, không bị bắt tạo khoá mới', async () => {
    mockApi((url) => (url.endsWith('/me') ? ok(me({ mfa_done: false, totp_enabled: false, totp_pending: true, permissions: [] })) : undefined));
    renderWithProviders(<App />);
    expect(await screen.findByLabelText('Mã 6 số')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Tạo khoá TOTP' })).toBeNull();
  });

  it('thành viên mới chưa có khoá thì phải tạo khoá trước', async () => {
    mockApi((url) => (url.endsWith('/me') ? ok(me({ mfa_done: false, totp_enabled: false, permissions: [] })) : undefined));
    renderWithProviders(<App />);
    expect(await screen.findByRole('button', { name: 'Tạo khoá TOTP' })).toBeTruthy();
    expect(screen.queryByLabelText('Mã 6 số')).toBeNull();
  });

  it('nav chỉ có mục vai trò được xem; số liệu trống hiện "—" chứ không bịa', async () => {
    mockApi((url) => {
      if (url.endsWith('/me')) return ok(me());
      if (url.includes('/copilot/usage')) return ok(emptyUsage);
      if (url.includes('/copilot/review-stats')) return ok(noReviews);
      return undefined;
    });
    renderWithProviders(<App />);
    expect(await screen.findByText('Chưa có lượt Copilot nào trong cửa sổ này')).toBeTruthy();
    const nav = screen.getByRole('navigation', { name: 'Mục chính' });
    expect(nav.textContent).toContain('Copilot Lab');
    expect(nav.textContent).not.toContain('Thành viên');
    expect(screen.getByText('Tỉ lệ đúng (người chấm)').nextSibling?.textContent).toBe('—');
  });

  it('vào thẳng URL không có quyền thì báo thiếu quyền', async () => {
    mockApi((url) => (url.endsWith('/me') ? ok(me()) : undefined));
    renderWithProviders(<App />, '/members');
    expect(await screen.findByText('Vai trò của bạn không mở được mục này')).toBeTruthy();
  });
});
