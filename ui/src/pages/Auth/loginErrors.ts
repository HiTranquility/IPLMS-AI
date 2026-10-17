import type { Messages } from '@/i18n/vi';

/** Mã lỗi Google callback trả trên URL (`?login_error=`) — chỉ mã, không có thông điệp từ server. */
export function loginErrorMessage(code: string | null, t: Messages): string | null {
  if (!code) return null;
  return t.login.errors[code] ?? t.login.errorFallback;
}
