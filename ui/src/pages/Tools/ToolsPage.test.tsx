import { fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { me, mockApi, ok, renderWithProviders } from '@/test/utils';
import { KnowledgePage } from '@/pages/Knowledge';
import { ToolsPage } from './ToolsPage';

const system = {
  checks: [
    { key: 'llm_key', label: 'Khoá nhà cung cấp LLM', ok: true },
    { key: 'google_oidc', label: 'Google OAuth client', ok: false },
  ],
  llm_model: 'gpt-x', telemetry_enabled: true, vision_device: 'cpu', telemetry_retention_days: 30, vision_retention_days: 90,
};

describe('ToolsPage', () => {
  it('analyst chỉ thấy kiểm cấu hình; không có form hỏi thử hay nạp tri thức', async () => {
    mockApi((url) => {
      if (url.endsWith('/me')) return ok(me({ permissions: ['ai:metrics:read'] }));
      if (url.endsWith('/tools/system')) return ok(system);
      return undefined;
    });
    renderWithProviders(<ToolsPage />);
    expect(await screen.findByText('Google OAuth client')).toBeTruthy();
    expect(screen.getByText('chưa cấu hình')).toBeTruthy();
    expect(screen.queryByRole('heading', { name: 'Hỏi thử Copilot' })).toBeNull();
    expect(screen.queryByRole('heading', { name: 'Nạp bản nháp tri thức' })).toBeNull();
  });

  it('nạp tri thức gửi multipart kèm header chống CSRF, không ép Content-Type JSON', async () => {
    const calls = mockApi((url) => {
      if (url.endsWith('/me')) return ok(me({ permissions: ['ai:metrics:read', 'ai:prompt:edit'] }));
      if (url.endsWith('/tools/system')) return ok(system);
      if (url.endsWith('/tools/knowledge/documents')) return ok({ documents: [] });
      if (url.endsWith('/tools/knowledge')) {
        return ok({ document_id: 'd', status: 'SUCCESS', ok: true, chunk_count: 4, duration_ms: 120, message: 'ok', version_id: 'v', version_no: 1 });
      }
      return undefined;
    });
    const user = userEvent.setup();
    renderWithProviders(<KnowledgePage />);
    const input = await screen.findByLabelText('Tệp PDF, DOCX, TXT hoặc MD (tối đa 8 MB)');
    await user.upload(input, new File(['# Quy chế'], 'quy-che.md', { type: 'text/markdown' }));
    // jsdom coi input file do user-event gán là còn trống (`valueMissing`) nên chặn submit bằng
    // nút; trình duyệt thật không bị — đã kiểm bằng Playwright. Ở đây submit form trực tiếp.
    fireEvent.submit(screen.getByRole('button', { name: 'Nạp bản nháp' }).closest('form')!);
    await waitFor(() => expect(calls.some((c) => c.url.endsWith('/tools/knowledge'))).toBe(true));
    const sent = calls.find((c) => c.url.endsWith('/tools/knowledge'))!;
    const headers = sent.init?.headers as Record<string, string>;
    expect(headers['X-Console-Request']).toBe('1');
    expect(headers['Content-Type']).toBeUndefined();
    const body = sent.init?.body as FormData;
    expect((body.get('file') as File).name).toBe('quy-che.md');
    expect(String(body.get('document_id'))).toMatch(/^[0-9a-f-]{36}$/);
    expect(await screen.findByText(/Đã tạo bản nháp v1/)).toBeTruthy();
  });
});
