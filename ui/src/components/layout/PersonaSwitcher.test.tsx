import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { me, renderWithProviders } from '@/test/utils';
import { setPersona } from '@/stores/useWorkspaceStore';
import { PersonaSwitcher } from './PersonaSwitcher';

describe('PersonaSwitcher — Multi-roles & Adaptive Layout', () => {
  beforeEach(() => {
    localStorage.clear();
    setPersona('all');
  });

  it('tài khoản chỉ có 1 vai trò (ai_annotator) chỉ hiện huy hiệu không gian cố định, không có dropdown', () => {
    const annotatorMe = me({
      roles: ['ai_annotator'],
      permissions: ['ai:task:label'],
    });

    renderWithProviders(<PersonaSwitcher me={annotatorMe} />);
    expect(screen.getByText('Xưởng Gán nhãn & Kiểm duyệt')).toBeTruthy();
    expect(screen.queryByRole('button', { name: /chuyển không gian làm việc/i })).toBeNull();
  });

  it('tài khoản Lead / Multi-roles hiện bộ chuyển đổi không gian làm việc', async () => {
    const user = userEvent.setup();
    const leadMe = me({
      roles: ['ai_lead', 'ai_console_admin', 'ai_ml_engineer', 'ai_annotator', 'ai_reviewer', 'ai_analyst', 'ai_data_engineer'],
      permissions: ['ai:member:manage', 'ai:audit:read', 'ai:task:label', 'ai:label:approve', 'ai:metrics:read', 'ai:chatlog:read'],
    });

    renderWithProviders(<PersonaSwitcher me={leadMe} />);
    const switcher = screen.getByRole('button', { name: /chuyển không gian làm việc/i });
    expect(switcher).toBeTruthy();

    // Mở menu chọn
    await user.click(switcher);
    expect(await screen.findByRole('menu')).toBeTruthy();
    expect(screen.getByText('Quản trị & Kiểm toán')).toBeTruthy();
    expect(screen.getByText('Kỹ sư ML & Huấn luyện')).toBeTruthy();
    expect(screen.getByText('Xưởng Gán nhãn & Kiểm duyệt')).toBeTruthy();
    expect(screen.getByText('Giám sát & Phân tích')).toBeTruthy();
  });

  it('chuyển sang Quản trị & Kiểm toán thì cập nhật persona', async () => {
    const user = userEvent.setup();
    const leadMe = me({
      roles: ['ai_lead', 'ai_console_admin', 'ai_ml_engineer'],
      permissions: ['ai:member:manage', 'ai:audit:read', 'ai:metrics:read'],
    });

    renderWithProviders(<PersonaSwitcher me={leadMe} />);
    const switcher = screen.getByRole('button', { name: /chuyển không gian làm việc/i });
    await user.click(switcher);

    const adminOption = screen.getByRole('menuitem', { name: /quản trị & kiểm toán/i });
    await user.click(adminOption);

    expect(localStorage.getItem('iplms_active_workspace')).toBe('admin');
  });
});
