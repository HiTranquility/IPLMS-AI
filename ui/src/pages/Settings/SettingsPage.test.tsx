import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { useState } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import { I18nProvider } from '@/i18n/I18nProvider';
import { DocumentPreviewDrawer } from '@/pages/Knowledge/components/DocumentPreviewDrawer';
import { KNOWLEDGE_MAX_FILE_BYTES, KnowledgePage } from '@/pages/Knowledge/KnowledgePage';
import { me, mockApi, ok, renderWithProviders } from '@/test/utils';
import SettingsPage from './SettingsPage';

describe('SettingsPage — WAI-ARIA Tabs & tabpanel (A-77, A-78, A-79)', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  function renderSettings() {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    return render(
      <QueryClientProvider client={queryClient}>
        <I18nProvider>
          <MemoryRouter initialEntries={['/settings']}>
            <SettingsPage />
          </MemoryRouter>
        </I18nProvider>
      </QueryClientProvider>,
    );
  }

  it('luôn render tabpanel đang chọn kể cả khi đang tải dữ liệu (A-78) và tablist có tên (A-79)', () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => {}));
    renderSettings();

    const tablist = screen.getByRole('tablist');
    expect(tablist.getAttribute('aria-label')).toBeTruthy();

    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(3);
    expect(tabs[0].getAttribute('aria-selected')).toBe('true');
    expect(tabs[0].getAttribute('aria-controls')).toBe('settings-panel-compute');

    const panel = screen.getByRole('tabpanel');
    expect(panel.getAttribute('id')).toBe('settings-panel-compute');
    expect(panel.getAttribute('aria-labelledby')).toBe('settings-tab-compute');
    expect(panel.getAttribute('tabIndex')).toBe('0');
  });

  it('phím ArrowRight / ArrowLeft chuyển tab đang chọn, dời focus và đổi tabpanel tương ứng (A-77)', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => {}));
    renderSettings();

    const tabs = screen.getAllByRole('tab');
    tabs[0].focus();
    expect(document.activeElement).toBe(tabs[0]);

    fireEvent.keyDown(tabs[0], { key: 'ArrowRight' });
    expect(tabs[1].getAttribute('aria-selected')).toBe('true');
    expect(tabs[0].getAttribute('aria-selected')).toBe('false');
    expect(document.activeElement).toBe(tabs[1]);
    expect(screen.getByRole('tabpanel').getAttribute('id')).toBe('settings-panel-policy');

    fireEvent.keyDown(tabs[1], { key: 'ArrowRight' });
    expect(tabs[2].getAttribute('aria-selected')).toBe('true');
    expect(document.activeElement).toBe(tabs[2]);
    expect(screen.getByRole('tabpanel').getAttribute('id')).toBe('settings-panel-security');

    fireEvent.keyDown(tabs[2], { key: 'ArrowLeft' });
    expect(tabs[1].getAttribute('aria-selected')).toBe('true');
    expect(document.activeElement).toBe(tabs[1]);
    expect(screen.getByRole('tabpanel').getAttribute('id')).toBe('settings-panel-policy');
  });
});

describe('SettingsPage — model đang chạy theo tác vụ (REQ-020 X2, ADR-0061 §2)', () => {
  it('hiện model inference dùng thật, không còn ô sửa provider/model', async () => {
    mockApi((url) => {
      if (url.endsWith('/me')) return ok(me({ permissions: ['ai:metrics:read', 'ai:prompt:edit'] }));
      if (url.endsWith('/tools/settings')) {
        return ok({
          hardware: {}, policy: {}, engines: {},
          compute: { profile: 'custom', vision_device: 'auto', onnx_enabled: true, vision_warmup_on_start: true,
            local_llm_gpu_layers: 33, local_llm_ctx_size: 4096, local_llm_threads: 4, local_llm_parallel_slots: 1 },
          models: [
            { task: 'copilot_answer', provider: 'openai', model: 'gpt-profile', source: 'profile', revision: 4 },
            { task: 'test_generation', provider: 'ollama', model: 'qwen2.5:0.5b', source: 'env', revision: null },
            { task: 'test_judge', provider: null, model: null, source: 'unknown', revision: null },
          ],
        });
      }
      return undefined;
    });
    renderWithProviders(<SettingsPage />);
    const table = await screen.findByRole('table', { name: 'Model đang chạy theo tác vụ' });
    expect(within(table).getByText('gpt-profile')).toBeTruthy();
    expect(within(table).getByText('Revision 4')).toBeTruthy();
    expect(within(table).getByText('Cấu hình env (dự phòng)')).toBeTruthy();
    expect(within(table).getByText('Không đọc được kho revision')).toBeTruthy();
    expect(document.getElementById('llm-model-input')).toBeNull();
    expect(document.getElementById('llm-provider-select')).toBeNull();
  });

  it('xác nhận thu hồi phiên ngay trên dòng thay vì window.confirm (AUDIT-007 B6)', async () => {
    const revoked: string[] = [];
    mockApi((url, init) => {
      if (url.endsWith('/me')) return ok(me({ permissions: ['ai:metrics:read', 'ai:member:manage'] }));
      if (url.endsWith('/tools/settings')) {
        return ok({ hardware: {}, policy: {}, engines: {}, compute: {}, models: [] });
      }
      if (url.endsWith('/tools/sessions')) {
        return ok(
          {
            session_id: 'sess-current',
            member_id: 'm-1',
            display_name: 'Admin 1',
            email: 'a1@iplms.internal',
            created_at: '2026-10-27T08:00:00Z',
            last_seen_at: '2026-10-27T08:05:00Z',
            mfa_verified: true,
            is_current: true,
          },
          {
            session_id: 'sess-other',
            member_id: 'm-2',
            display_name: 'Member 2',
            email: 'm2@iplms.internal',
            created_at: '2026-10-27T07:00:00Z',
            last_seen_at: '2026-10-27T07:30:00Z',
            mfa_verified: true,
            is_current: false,
          },
        );
      }
      if (url.includes('/tools/sessions/sess-other/revoke') && init?.method === 'POST') {
        revoked.push('sess-other');
        return ok({ session_id: 'sess-other', revoked: true });
      }
      return undefined;
    });

    renderWithProviders(<SettingsPage />);
    fireEvent.click(screen.getByRole('tab', { name: /Phiên đăng nhập/i }));
    const revokeBtn = await screen.findByRole('button', { name: /Thu hồi phiên #2 của Member 2/i });
    fireEvent.click(revokeBtn);

    // Hiện nút Xác nhận và Hủy ngay trên dòng
    const cancelBtn = screen.getByRole('button', { name: 'Hủy' });
    expect(screen.getByRole('button', { name: 'Xác nhận' })).toBeTruthy();
    fireEvent.click(cancelBtn);
    expect(revoked).toHaveLength(0);

    // Mở lại và bấm Xác nhận
    fireEvent.click(screen.getByRole('button', { name: /Thu hồi phiên #2 của Member 2/i }));
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Xác nhận' }));
    });
    await waitFor(() => {
      expect(revoked).toEqual(['sess-other']);
      expect(screen.queryByRole('button', { name: 'Xác nhận' })).toBeNull();
    });
  });
});

describe('KnowledgePage & DocumentPreviewDrawer (AUDIT-007 B5, B7)', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('DocumentPreviewDrawer focus nút đóng khi mở và trả focus về nút mở khi đóng (AUDIT-007 B5)', async () => {
    mockApi((url) => {
      if (url.includes('/tools/knowledge/documents/')) {
        return ok({ document_id: 'doc-1', version_no: 1, total: 0, chunks: [] });
      }
      return undefined;
    });

    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <div>
          <button type="button" onClick={() => setOpen(true)}>
            Mở xem trước
          </button>
          <DocumentPreviewDrawer
            document={
              open
                ? {
                    id: 'doc-1',
                    title: 'Quy chế bãi xe',
                    source: 'quy-che.pdf',
                    category: 'regulation',
                    chunk_count: 1,
                    content: 'Nội dung mẫu',
                  }
                : null
            }
            onClose={() => setOpen(false)}
          />
        </div>
      );
    }

    renderWithProviders(<Harness />);
    const triggerBtn = screen.getByRole('button', { name: 'Mở xem trước' });
    triggerBtn.focus();
    expect(document.activeElement).toBe(triggerBtn);

    fireEvent.click(triggerBtn);
    const closeBtn = screen.getByRole('button', { name: 'Đóng ngăn kéo xem trước' });
    expect(document.activeElement).toBe(closeBtn);

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(document.activeElement).toBe(triggerBtn);
  });

  it('KnowledgePage báo lỗi ngay trên dòng khi chọn tệp vượt 8 MB và khoá nút nạp (AUDIT-007 B7)', async () => {
    mockApi((url) => {
      if (url.includes('/tools/knowledge/documents')) return ok();
      return undefined;
    });

    renderWithProviders(<KnowledgePage />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const bigFile = new File(['x'], 'oversized.pdf', { type: 'application/pdf' });
    Object.defineProperty(bigFile, 'size', { value: KNOWLEDGE_MAX_FILE_BYTES + 1024 });

    fireEvent.change(input, { target: { files: [bigFile] } });
    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('oversized.pdf');
    expect(alert.textContent).toContain('8 MB');

    const submitBtn = screen.getByRole('button', { name: 'Nạp bản nháp' });
    expect((submitBtn as HTMLButtonElement).disabled).toBe(true);
  });
});
