import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import { I18nProvider } from '@/i18n/I18nProvider';
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
});
