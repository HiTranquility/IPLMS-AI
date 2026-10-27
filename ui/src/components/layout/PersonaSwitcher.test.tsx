import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { me, renderWithProviders } from '@/test/utils';
import { setPersona } from '@/stores/useWorkspaceStore';
import type { Me } from '@/types/auth';
import { AppShell } from './AppShell';
import { getAvailablePersonas } from './navigation';
import { PersonaSwitcher } from './PersonaSwitcher';

describe('PersonaSwitcher — Multi-roles & Adaptive Layout', () => {
  beforeEach(() => {
    localStorage.clear();
    setPersona('all', 'm-1');
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

    expect(localStorage.getItem('iplms_active_workspace:m-1')).toBe('admin');
  });
});

describe('Không gian làm việc theo từng tài khoản (ai bug-041)', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('tài khoản sau không thừa hưởng không gian của tài khoản trước trên cùng trình duyệt', () => {
    // Lead chọn Focus Mode gán nhãn rồi đăng xuất.
    setPersona('labeling', 'm-lead');
    const mlEngineer = me({
      member_id: 'm-ml',
      roles: ['ai_ml_engineer'],
      permissions: ['ai:metrics:read', 'ai:chatlog:read', 'ai:model:evaluate', 'ai:prompt:edit', 'ai:dataset:snapshot'],
    });

    renderWithProviders(<AppShell me={mlEngineer}>nội dung</AppShell>);

    expect(screen.getByRole('link', { name: /Dự báo & Giá động/ })).toBeTruthy();
    expect(screen.getByRole('link', { name: /Model & lượt đo/ })).toBeTruthy();
    expect(screen.getByRole('link', { name: /Công cụ thử/ })).toBeTruthy();
  });

  it('không gian đã lưu không còn thuộc tài khoản thì quay về không gian của tài khoản đó', () => {
    setPersona('labeling', 'm-ml2');
    const mlEngineer = me({
      member_id: 'm-ml2',
      roles: ['ai_ml_engineer'],
      permissions: ['ai:metrics:read', 'ai:model:evaluate'],
    });

    renderWithProviders(<AppShell me={mlEngineer}>nội dung</AppShell>);

    expect(screen.getByRole('link', { name: /Model & lượt đo/ })).toBeTruthy();
    expect(screen.queryByRole('link', { name: /Gán nhãn/ })).toBeNull();
  });

  it('chia không gian theo vai', () => {
    const of = (roles: Me['roles']) => getAvailablePersonas(me({ roles, permissions: [] }));
    expect(of(['ai_annotator'])).toEqual(['labeling']);
    expect(of(['ai_analyst'])).toEqual(['analytics']);
    expect(of(['ai_data_engineer'])).toEqual(['ml']);
    expect(of(['ai_console_admin'])).toEqual(['admin']);
    expect(of(['ai_reviewer'])).toEqual(['all', 'labeling', 'analytics']);
    expect(of(['ai_lead'])).toEqual(['all', 'admin', 'ml', 'labeling', 'analytics']);
    expect(of([])).toEqual(['all']);
  });
});
