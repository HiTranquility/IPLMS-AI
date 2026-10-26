import { describe, expect, it, vi } from 'vitest';
import { fail, mockApi, ok } from '@/test/utils';
import { ApiError, request, requestOne } from './client';

describe('request', () => {
  it('request ghi gắn header chống CSRF, request đọc thì không', async () => {
    const calls = mockApi(() => ok({ changed: true }));
    await request('/members/m/roles/ai_lead', { method: 'POST', body: { reason: 'abc' } });
    await request('/me');
    const [write, read] = calls;
    expect((write.init?.headers as Record<string, string>)['X-Console-Request']).toBe('1');
    expect(write.init?.credentials).toBe('same-origin');
    expect(write.url).toBe('/api/members/m/roles/ai_lead');
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

  it('đứt mạng hoặc timeout khi fetch ném ApiError mã NETWORK (status 0)', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('Failed to fetch'));
    await expect(request('/copilot/turns')).rejects.toMatchObject({
      status: 0,
      code: 'NETWORK',
      message: 'Không kết nối được tới AI Console. Process console có đang chạy không?',
      fromServer: false,
    });
  });

  it('máy chủ lỗi 500 trả về HTML/rỗng không phải JSON vẫn báo HTTP_500 an toàn', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response('Internal Server Error', { status: 500, headers: { 'Content-Type': 'text/plain' } }),
    );
    await expect(request('/copilot/turns')).rejects.toMatchObject({
      status: 500,
      code: 'HTTP_500',
      message: 'Máy chủ console trả lỗi 500.',
      fromServer: false,
    });
  });

  it('lỗi 403 FORBIDDEN giữ nguyên mã và thông điệp từ chối quyền của server', async () => {
    mockApi(() => fail(403, 'FORBIDDEN', 'Bạn không có quyền thực hiện thao tác này.'));
    await expect(request('/copilot/turns/123/review', { method: 'POST', body: {} })).rejects.toMatchObject({
      status: 403,
      code: 'FORBIDDEN',
      message: 'Bạn không có quyền thực hiện thao tác này.',
      fromServer: true,
    });
  });

  it('requestOne khi server trả mảng data rỗng ném ApiError mã EMPTY', async () => {
    mockApi(() => ok());
    await expect(requestOne('/me')).rejects.toMatchObject({
      status: 500,
      code: 'EMPTY',
      message: 'Máy chủ không trả dữ liệu.',
    });
  });
});
