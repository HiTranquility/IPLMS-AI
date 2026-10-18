import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { ApiError } from '@/api/client';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { fail, me, mockApi, ok, renderWithProviders } from '@/test/utils';
import { applyLang } from '@/utils/lang';
import { App } from '../App';
import { en } from './en';
import { vi as viDict } from './vi';

const emptyUsage = {
  window_days: 7, total_requests: 0, success_requests: 0, refused_requests: 0, no_context_requests: 0,
  error_requests: 0, avg_latency_ms: 0, p95_latency_ms: 0, input_tokens: 0, output_tokens: 0,
  cost_known: false, total_cost_usd: 0, avg_cost_usd: 0, thumbs_up: 0, thumbs_down: 0, days: [],
};
const noReviews = { window_days: 7, reviewed: 0, correct: 0, incorrect: 0, unsafe: 0, accuracy: null };

describe('VI/EN', () => {
  it('đổi sang EN ở rail thì nav đổi chữ, <html lang> và lựa chọn được nhớ', async () => {
    mockApi((url) => {
      if (url.endsWith('/me')) return ok(me());
      if (url.includes('/copilot/usage')) return ok(emptyUsage);
      if (url.includes('/copilot/review-stats')) return ok(noReviews);
      return undefined;
    });
    renderWithProviders(<App />);
    await screen.findByText(viDict.overview.emptyTitle);
    await userEvent.setup().click(screen.getByRole('button', { name: 'EN' }));

    expect(await screen.findByText(en.overview.emptyTitle)).toBeTruthy();
    const nav = screen.getByRole('navigation', { name: en.shell.navLabel });
    expect(within(nav).getByText(en.nav.visionOverview)).toBeTruthy();
    expect(document.documentElement.lang).toBe('en');
    expect(localStorage.getItem('ai-console-lang')).toBe('en');
  });

  it('trang đăng nhập có nút đổi ngôn ngữ trước khi vào console', async () => {
    mockApi(() => fail(401, 'UNAUTHENTICATED'));
    renderWithProviders(<App />);
    await screen.findByRole('link', { name: viDict.login.google });
    await userEvent.setup().click(screen.getByRole('button', { name: 'EN' }));
    expect(await screen.findByRole('link', { name: en.login.google })).toBeTruthy();
  });

  it('lỗi server (tiếng Việt) ở EN: câu dịch theo code, giữ nguyên văn và mã', () => {
    applyLang('en');
    const error = new ApiError(403, 'FORBIDDEN', 'Vai trò không có quyền này.', true);
    renderWithProviders(<ErrorBlock error={error} />);
    expect(screen.getByText(en.errors.serverCodes.FORBIDDEN)).toBeTruthy();
    expect(screen.getByText('Vai trò không có quyền này.')).toBeTruthy();
    expect(screen.getByText(en.feedback.code('FORBIDDEN'))).toBeTruthy();
  });

  it('lỗi server ở VI: hiện thẳng thông điệp server, không thêm dòng dịch', () => {
    const error = new ApiError(403, 'FORBIDDEN', 'Vai trò không có quyền này.', true);
    renderWithProviders(<ErrorBlock error={error} />);
    expect(screen.getByText('Vai trò không có quyền này.')).toBeTruthy();
    expect(screen.queryByText(viDict.feedback.serverSaid, { exact: false })).toBeNull();
  });
});
