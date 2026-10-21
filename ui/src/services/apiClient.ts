import { messages } from '@/i18n/I18nProvider';
import type { ApiEnvelope } from '@/types/api';

/** Gọi API console cùng nguồn (/console/api). Cookie phiên httpOnly đi kèm tự động. */
export const API_BASE = '/console/api';

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  /** `message` do server viết (luôn tiếng Việt), không phải câu client tự đặt theo ngôn ngữ đang dùng. */
  readonly fromServer: boolean;

  constructor(status: number, code: string, message: string, fromServer = false) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.fromServer = fromServer;
  }
}

function messageOf(status: number, body: Partial<ApiEnvelope<unknown>> | null): string {
  if (body?.message) return body.message;
  // FastAPI trả {"detail": [...]} khi body/query sai kiểu (422).
  if (status === 422) return messages().errors.invalidData;
  return messages().errors.http(status);
}

export async function request<T>(path: string, init: { method?: 'GET' | 'POST'; body?: unknown } = {}): Promise<T[]> {
  const method = init.method ?? 'GET';
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (method !== 'GET') {
    // Chống CSRF: backend từ chối request ghi thiếu header này (console_access.py).
    headers['X-Console-Request'] = '1';
    // FormData (tải tệp): để trình duyệt tự đặt multipart boundary.
    if (init.body !== undefined && !(init.body instanceof FormData)) headers['Content-Type'] = 'application/json';
  }
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      credentials: 'same-origin',
      body: init.body === undefined ? undefined : init.body instanceof FormData ? init.body : JSON.stringify(init.body),
    });
  } catch {
    throw new ApiError(0, 'NETWORK', messages().errors.network);
  }
  const body = (await response.json().catch(() => null)) as Partial<ApiEnvelope<T>> | null;
  if (!response.ok || body?.success === false) {
    throw new ApiError(response.status, body?.code ?? `HTTP_${response.status}`, messageOf(response.status, body), Boolean(body?.message));
  }
  return body?.data ?? [];
}

export async function requestOne<T>(path: string, init?: Parameters<typeof request>[1]): Promise<T> {
  const [first] = await request<T>(path, init);
  if (first === undefined) throw new ApiError(500, 'EMPTY', messages().errors.empty);
  return first;
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path, { method: 'GET' }),
  getOne: <T>(path: string) => requestOne<T>(path, { method: 'GET' }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  postOne: <T>(path: string, body?: unknown) => requestOne<T>(path, { method: 'POST', body }),
};

export default apiClient;
