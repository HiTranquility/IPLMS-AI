import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { me, renderWithProviders } from '@/test/utils';
import { AppShell } from './AppShell';

// SUGGESTION-003: rail thành ngăn kéo dưới 768px. jsdom không áp CSS media nên test hành vi,
// còn bố cục 375/768/1280 kiểm bằng Playwright.
describe('AppShell — ngăn kéo điều hướng', () => {
  const lead = me({ roles: ['ai_lead'], permissions: ['ai:metrics:read', 'ai:audit:read'] });

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

  it('bấm lớp phủ hoặc nút đóng thì ngăn kéo đóng', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AppShell me={lead}>nội dung</AppShell>);
    const menu = screen.getByRole('button', { name: 'Mở menu' });

    await user.click(menu);
    const closers = screen.getAllByRole('button', { name: 'Đóng menu' });
    expect(closers.length).toBe(2); // lớp phủ + nút X trong ngăn kéo
    await user.click(closers[closers.length - 1]);
    expect(menu.getAttribute('aria-expanded')).toBe('false');
    expect(screen.getAllByRole('button', { name: 'Đóng menu' }).length).toBe(1); // lớp phủ đã gỡ
  });
});
