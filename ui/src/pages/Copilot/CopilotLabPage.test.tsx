import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { Turn } from '@/api/types';
import { fail, me, mockApi, ok, renderWithProviders } from '@/test/utils';
import { CopilotLabPage } from './CopilotLabPage';

const turn: Turn = {
  turn_id: '3f1c2a64-5b7d-4e8f-9a01-23456789abcd', at: '2026-10-16T03:00:00+00:00', task: 'copilot_ask',
  status: 'SUCCESS', model: 'm', prompt_version: 'copilot_rag_system#abcd1234', input_tokens: 10,
  output_tokens: 5, latency_ms: 120, cost_usd: null, user_role: 'member', parking_lot_id: '',
  query: 'Phí gửi xe [PLATE] ngày lễ?', answer: 'Phí 20.000đ', error_code: '', feedback: -1, review: null,
};

function setup(permissions = me().permissions) {
  return mockApi((url) => {
    if (url.endsWith('/me')) return ok(me({ permissions }));
    if (url.includes('/copilot/turns?')) return ok(turn);
    if (url.endsWith('/review')) return ok({ turn_id: turn.turn_id, verdict: 'INCORRECT' });
    return undefined;
  });
}

describe('CopilotLabPage', () => {
  it('chấm "Sai" phải có ghi chú rồi mới gửi được, gửi đúng verdict + note', async () => {
    const calls = setup();
    const user = userEvent.setup();
    renderWithProviders(<CopilotLabPage />);
    await user.click(await screen.findByRole('button', { name: /Phí gửi xe/ }));
    await user.click(screen.getByRole('radio', { name: 'Sai' }));
    const save = screen.getByRole('button', { name: 'Lưu kết quả' });
    expect(save).toHaveProperty('disabled', true);

    await user.type(screen.getByLabelText('Ghi chú'), 'ngày lễ giá 30.000đ');
    await user.click(save);
    await waitFor(() => expect(calls.some((c) => c.url.endsWith('/review'))).toBe(true));
    const sent = calls.find((c) => c.url.endsWith('/review'));
    expect(JSON.parse(String(sent?.init?.body))).toEqual({ verdict: 'INCORRECT', note: 'ngày lễ giá 30.000đ' });
    expect(await screen.findByText('Đã lưu kết quả chấm.')).toBeTruthy();
  });

  it('analyst xem được lượt nhưng không có form chấm', async () => {
    setup(['ai:metrics:read', 'ai:chatlog:read']);
    const user = userEvent.setup();
    renderWithProviders(<CopilotLabPage />);
    await user.click(await screen.findByRole('button', { name: /Phí gửi xe/ }));
    expect(screen.getByText('Phí 20.000đ')).toBeTruthy();
    await waitFor(() => expect(screen.queryByRole('form', { name: 'Chấm lượt trả lời' })).toBeNull());
    expect(screen.getByText('Chỉ Reviewer hoặc AI Lead chấm được lượt này.')).toBeTruthy();
  });

  it('lọc theo phản hồi gửi feedback=-1 lên API', async () => {
    const calls = setup();
    const user = userEvent.setup();
    renderWithProviders(<CopilotLabPage />);
    await screen.findByRole('button', { name: /Phí gửi xe/ });
    await user.click(screen.getByRole('button', { name: 'Chưa đúng' }));
    await waitFor(() => expect(calls.some((c) => c.url.includes('feedback=-1'))).toBe(true));
  });

  it('khi API tải danh sách lượt trả lỗi 500 thì hiện khối lỗi và bấm "Thử lại" phục hồi được', async () => {
    let attempts = 0;
    mockApi((url) => {
      if (url.endsWith('/me')) return ok(me());
      if (url.includes('/copilot/turns?')) {
        attempts += 1;
        return attempts === 1
          ? fail(500, 'INTERNAL_ERROR', 'Không truy cập được telemetry AI.')
          : ok(turn);
      }
      return undefined;
    });
    const user = userEvent.setup();
    renderWithProviders(<CopilotLabPage />);

    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('Không truy cập được telemetry AI.');
    expect(alert.textContent).toContain('Mã: INTERNAL_ERROR');

    await user.click(screen.getByRole('button', { name: 'Thử lại' }));
    expect(await screen.findByRole('button', { name: /Phí gửi xe/ })).toBeTruthy();
    expect(attempts).toBe(2);
  });

  it('khi gửi chấm điểm bị chặn 403 FORBIDDEN thì báo lỗi trung thực, không báo lưu thành công giả', async () => {
    mockApi((url) => {
      if (url.endsWith('/me')) return ok(me());
      if (url.includes('/copilot/turns?')) return ok(turn);
      if (url.endsWith('/review')) return fail(403, 'FORBIDDEN', 'Bạn không có quyền thực hiện thao tác này.');
      return undefined;
    });
    const user = userEvent.setup();
    renderWithProviders(<CopilotLabPage />);

    await user.click(await screen.findByRole('button', { name: /Phí gửi xe/ }));
    await user.click(screen.getByRole('button', { name: 'Lưu kết quả' }));

    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('Bạn không có quyền thực hiện thao tác này.');
    expect(alert.textContent).toContain('Mã: FORBIDDEN');
    expect(screen.queryByText('Đã lưu kết quả chấm.')).toBeNull();
  });

  it('khi phiên hết hạn (401 NO_SESSION) lúc lưu kết quả chấm thì báo mã NO_SESSION và không báo đã lưu', async () => {
    mockApi((url) => {
      if (url.endsWith('/me')) return ok(me());
      if (url.includes('/copilot/turns?')) return ok(turn);
      if (url.endsWith('/review')) return fail(401, 'NO_SESSION', 'Phiên đã hết hạn, vui lòng đăng nhập lại.');
      return undefined;
    });
    const user = userEvent.setup();
    renderWithProviders(<CopilotLabPage />);

    await user.click(await screen.findByRole('button', { name: /Phí gửi xe/ }));
    await user.click(screen.getByRole('button', { name: 'Lưu kết quả' }));

    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('Phiên đã hết hạn, vui lòng đăng nhập lại.');
    expect(alert.textContent).toContain('Mã: NO_SESSION');
    expect(screen.queryByText('Đã lưu kết quả chấm.')).toBeNull();
  });

  it('thanh tìm kiếm lọc danh sách câu hỏi theo từ khoá', async () => {
    setup();
    const user = userEvent.setup();
    renderWithProviders(<CopilotLabPage />);

    expect(await screen.findByRole('button', { name: /Phí gửi xe/ })).toBeTruthy();
    const searchInput = screen.getByPlaceholderText('Tìm kiếm theo câu hỏi, câu trả lời, mã lượt...');
    await user.type(searchInput, 'từ_khoá_không_tồn_tại_123');

    // Không còn thấy lượt cũ
    expect(screen.queryByRole('button', { name: /Phí gửi xe/ })).toBeNull();

    // Xoá tìm kiếm thì lượt quay lại
    await user.click(screen.getByRole('button', { name: 'Xoá tìm kiếm' }));
    expect(await screen.findByRole('button', { name: /Phí gửi xe/ })).toBeTruthy();
  });

  it('dải tiến độ thẩm định hiển thị đúng số lượt và tỉ lệ', async () => {
    setup();
    renderWithProviders(<CopilotLabPage />);

    expect(await screen.findByText('Tiến độ thẩm định câu hỏi')).toBeTruthy();
    expect(screen.getByText('0 / 1 (0%)')).toBeTruthy();
  });

  it('bấm nút 1-click [1] Đúng gửi kết quả chấm ngay', async () => {
    const calls = setup();
    const user = userEvent.setup();
    renderWithProviders(<CopilotLabPage />);

    await user.click(await screen.findByRole('button', { name: /Phí gửi xe/ }));
    const quickCorrectBtn = screen.getByRole('button', { name: '[1] Đúng' });
    await user.click(quickCorrectBtn);

    await waitFor(() => expect(calls.some((c) => c.url.endsWith('/review'))).toBe(true));
    const sent = calls.find((c) => c.url.endsWith('/review'));
    expect(JSON.parse(String(sent?.init?.body))).toEqual({ verdict: 'CORRECT', note: '' });
  });

  it('gắn nhanh lý do từ chối điền vào ô ghi chú', async () => {
    setup();
    const user = userEvent.setup();
    renderWithProviders(<CopilotLabPage />);

    await user.click(await screen.findByRole('button', { name: /Phí gửi xe/ }));
    await user.click(screen.getByRole('button', { name: '[2] Sai' }));

    const tagFeeBtn = screen.getByRole('button', { name: 'Sai biểu phí' });
    await user.click(tagFeeBtn);

    const noteInput = screen.getByLabelText('Ghi chú') as HTMLTextAreaElement;
    expect(noteInput.value).toContain('Sai biểu phí');
  });
});
