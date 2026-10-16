/** Gọi API console cùng nguồn (/console/api). Cookie phiên httpOnly đi kèm tự động. */
export const API_BASE = '/console/api';

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

interface Envelope<T> {
  success: boolean;
  message: string;
  data: T[];
  code?: string;
  detail?: unknown;
}

function messageOf(status: number, body: Partial<Envelope<unknown>> | null): string {
  if (body?.message) return body.message;
  // FastAPI trả {"detail": [...]} khi body/query sai kiểu (422).
  if (status === 422) return 'Dữ liệu gửi lên chưa hợp lệ.';
  return `Máy chủ console trả lỗi ${status}.`;
}

export async function request<T>(path: string, init: { method?: 'GET' | 'POST'; body?: unknown } = {}): Promise<T[]> {
  const method = init.method ?? 'GET';
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (method !== 'GET') {
    // Chống CSRF: backend từ chối request ghi thiếu header này (console_access.py).
    headers['X-Console-Request'] = '1';
    if (init.body !== undefined) headers['Content-Type'] = 'application/json';
  }
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      credentials: 'same-origin',
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
    });
  } catch {
    throw new ApiError(0, 'NETWORK', 'Không kết nối được tới AI Console. Process console có đang chạy không?');
  }
  const body = (await response.json().catch(() => null)) as Partial<Envelope<T>> | null;
  if (!response.ok || body?.success === false) {
    throw new ApiError(response.status, body?.code ?? `HTTP_${response.status}`, messageOf(response.status, body));
  }
  return body?.data ?? [];
}

export async function requestOne<T>(path: string, init?: Parameters<typeof request>[1]): Promise<T> {
  const [first] = await request<T>(path, init);
  if (first === undefined) throw new ApiError(500, 'EMPTY', 'Máy chủ không trả dữ liệu.');
  return first;
}
