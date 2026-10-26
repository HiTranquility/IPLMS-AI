import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { me, renderWithProviders } from '@/test/utils';
import { AppShell } from './AppShell';

// SUGGESTION-003: rail thành ngăn kéo dưới 768px. jsdom không áp CSS media nên test hành vi,
// còn bố cục 375/768/1280 kiểm bằng Playwright.
describe('AppShell — ngăn kéo điều hướng & thu gọn rail', () => {
  const lead = me({ roles: ['ai_lead'], permissions: ['ai:metrics:read', 'ai:audit:read'] });

  beforeEach(() => {
    localStorage.clear();
  });

  it('nút menu mở ngăn kéo, focus vào trong, Esc đóng và trả focus về nút menu', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AppShell me={lead}>nội dung</AppShell>);
    const menu = screen.getByRole('button', { name: 'Mở menu' });
    expect(menu.getAttribute('aria-expanded')).toBe('false');

    await user.click(menu);
    expect(menu.getAttribute('aria-expanded')).toBe('true');
    const rail = document.getElementById('console-rail')!;
    await waitFor(() => expect(rail.contains(document.activeElement)).toBe(true));

    await user.keyboard('{Escape}');
    expect(menu.getAttribute('aria-expanded')).toBe('false');
    await waitFor(() => expect(document.activeElement).toBe(menu));
  });

  it('bấm lớp phủ thì ngăn kéo đóng', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AppShell me={lead}>nội dung</AppShell>);
    const menu = screen.getByRole('button', { name: 'Mở menu' });

    await user.click(menu);
    const scrim = screen.getByRole('button', { name: 'Đóng menu' });
    expect(scrim).toBeTruthy(); // lớp phủ (scrim)
    await user.click(scrim);
    expect(menu.getAttribute('aria-expanded')).toBe('false');
    expect(screen.queryByRole('button', { name: 'Đóng menu' })).toBeNull();
  });

  it('có nút thu gọn / mở rộng điều hướng và nút icon Cài đặt cạnh nút đổi giao diện', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AppShell me={lead}>nội dung</AppShell>);

    const collapseBtn = screen.getByRole('button', { name: 'Thu gọn / Mở rộng điều hướng' });
    expect(collapseBtn.getAttribute('aria-expanded')).toBe('true');

    await user.click(collapseBtn);
    expect(collapseBtn.getAttribute('aria-expanded')).toBe('false');
    expect(localStorage.getItem('iplms_rail_collapsed')).toBe('true');

    const settingsBtn = screen.getByRole('button', { name: 'Cài đặt & Phần cứng' });
    expect(settingsBtn).toBeTruthy();
  });
});
