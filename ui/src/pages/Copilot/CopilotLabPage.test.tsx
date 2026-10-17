import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { Turn } from '@/api/types';
import { me, mockApi, ok, renderWithProviders } from '@/test/utils';
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
});
