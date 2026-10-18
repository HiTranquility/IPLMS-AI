export type Lang = 'vi' | 'en';
const KEY = 'ai-console-lang';

// Ngôn ngữ đang dùng cho code ngoài React (format.ts, client.ts); React đọc qua useI18n.
let current: Lang = 'vi';

export const currentLang = (): Lang => current;

/** Việt-first như frontend: chỉ đổi khi người dùng đã chọn EN ở rail hoặc trang đăng nhập. */
export function initialLang(): Lang {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === 'vi' || saved === 'en') return saved;
  } catch {
    /* storage bị chặn: dùng tiếng Việt */
  }
  return 'vi';
}

export function applyLang(lang: Lang) {
  current = lang;
  document.documentElement.lang = lang;
  try {
    localStorage.setItem(KEY, lang);
  } catch {
    /* không lưu được thì chỉ áp cho phiên này */
  }
}
