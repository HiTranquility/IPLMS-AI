/** Mã lỗi Google callback trả trên URL (`?login_error=`) — chỉ mã, không có thông điệp từ server. */
const MESSAGES: Record<string, string> = {
  GOOGLE_DENIED: 'Bạn đã huỷ hoặc Google từ chối đăng nhập.',
  NOT_INVITED: 'Email Google này chưa được mời vào console.',
  NOT_CONFIGURED: 'Console chưa cấu hình đăng nhập Google. Dùng tài khoản khẩn cấp hoặc báo người vận hành.',
  MEMBER_DISABLED: 'Tài khoản console đã bị khoá.',
  UNAUTHENTICATED: 'Đăng nhập Google không hoàn tất (phiên quá 10 phút hoặc không khớp). Thử lại.',
};

export function loginErrorMessage(code: string | null): string | null {
  if (!code) return null;
  return MESSAGES[code] ?? 'Đăng nhập không thành công. Thử lại.';
}
