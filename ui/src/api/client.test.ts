import { describe, expect, it } from 'vitest';
import { fail, mockApi, ok } from '@/test/utils';
import { ApiError, request } from './client';

describe('request', () => {
  it('request ghi gắn header chống CSRF, request đọc thì không', async () => {
    const calls = mockApi(() => ok({ changed: true }));
    await request('/members/m/roles/ai_lead', { method: 'POST', body: { reason: 'abc' } });
    await request('/me');
    const [write, read] = calls;
    expect((write.init?.headers as Record<string, string>)['X-Console-Request']).toBe('1');
    expect(write.init?.credentials).toBe('same-origin');
    expect(write.url).toBe('/console/api/members/m/roles/ai_lead');
    expect((read.init?.headers as Record<string, string>)['X-Console-Request']).toBeUndefined();
  });

  it('lỗi envelope thành ApiError mang mã và thông điệp của server', async () => {
    mockApi(() => fail(401, 'MFA_REQUIRED', 'Cần nhập mã TOTP.'));
    await expect(request('/me')).rejects.toMatchObject({ status: 401, code: 'MFA_REQUIRED', message: 'Cần nhập mã TOTP.' });
  });

  it('422 của FastAPI không có message vẫn ra câu tiếng Việt', async () => {
    mockApi(() => ({ status: 422, body: { detail: [{ loc: ['body', 'reason'] }] } }));
    const error = await request('/members', { method: 'POST', body: {} }).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).message).toBe('Dữ liệu gửi lên chưa hợp lệ.');
  });
});
