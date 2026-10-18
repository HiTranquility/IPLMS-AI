import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import type { Me } from '@/api/types';
import { I18nProvider } from '@/i18n/I18nProvider';

type Route = (url: string, init?: RequestInit) => { status?: number; body: unknown } | undefined;

/** Giả `fetch` theo đường dẫn; ghi lại mọi request để kiểm header/body. */
export function mockApi(route: Route) {
  const calls: { url: string; init?: RequestInit }[] = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input);
    calls.push({ url, init });
    const hit = route(url, init);
    if (!hit) return new Response(JSON.stringify({ success: false, message: `no mock: ${url}`, data: [] }), { status: 404 });
    return new Response(JSON.stringify(hit.body), { status: hit.status ?? 200 });
  });
  return calls;
}

export const ok = <T,>(...data: T[]) => ({ body: { success: true, total: data.length, message: 'OK', data } });
export const fail = (status: number, code: string, message = 'lỗi') => ({ status, body: { success: false, total: 0, message, data: [], code } });

export function me(overrides: Partial<Me> = {}): Me {
  return {
    member_id: 'm-1',
    email: 'rv@x.vn',
    display_name: 'Người chấm',
    roles: ['ai_reviewer'],
    permissions: ['ai:metrics:read', 'ai:task:label', 'ai:label:approve', 'ai:chatlog:read'],
    mfa_done: true,
    totp_enabled: true,
    totp_pending: false,
    ...overrides,
  };
}

export function renderWithProviders(ui: ReactNode, path = '/') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <I18nProvider>
        <MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>
      </I18nProvider>
    </QueryClientProvider>,
  );
}
