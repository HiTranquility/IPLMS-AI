import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';
import { applyLang } from '@/utils/lang';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  // Mỗi test bắt đầu lại bằng tiếng Việt, không mang lựa chọn EN của test trước.
  applyLang('vi');
  localStorage.clear();
});
