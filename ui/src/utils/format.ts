import { currentLang, type Lang } from './lang';

const TZ = 'Asia/Ho_Chi_Minh';
const LOCALE: Record<Lang, string> = { vi: 'vi-VN', en: 'en-US' };
const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 4 });

function build(locale: string) {
  return {
    integer: new Intl.NumberFormat(locale),
    decimal: new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }),
    percent: new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 1 }),
    date: new Intl.DateTimeFormat(locale, { timeZone: TZ, day: '2-digit', month: '2-digit', year: '2-digit' }),
    time: new Intl.DateTimeFormat(locale, { timeZone: TZ, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }),
    day: new Intl.DateTimeFormat(locale, { timeZone: 'UTC', weekday: 'short', day: '2-digit', month: '2-digit' }),
    dayMonth: new Intl.DateTimeFormat(locale, { timeZone: 'UTC', day: '2-digit', month: '2-digit' }),
  };
}

const cache: Partial<Record<Lang, ReturnType<typeof build>>> = {};
const f = () => (cache[currentLang()] ??= build(LOCALE[currentLang()]));

export const DASH = '—';

export const fmtInt = (n: number | null | undefined) => (n == null ? DASH : f().integer.format(n));
export const fmtMs = (n: number | null | undefined) => (n == null ? DASH : `${f().decimal.format(n)} ms`);
export const fmtPercent = (n: number | null | undefined) => (n == null ? DASH : f().percent.format(n));
export const fmtUsd = (n: number | null | undefined) => (n == null ? DASH : usd.format(n));
// Ngày trước giờ, không giây (ISSUE-005): vi-VN mặc định đặt giờ trước ngày, khó quét theo cột.
export const fmtDateTime = (iso: string) => {
  const d = new Date(iso);
  return `${f().date.format(d)} ${f().time.format(d)}`;
};
// `date` của chuỗi ngày đã là ngày theo giờ Việt Nam (server gom theo Asia/Ho_Chi_Minh).
export const fmtDay = (isoDate: string) => f().day.format(new Date(`${isoDate}T00:00:00Z`));
/** Nhãn trục ngày: chỉ ngày/tháng, không cắt chuỗi Intl (độ dài đổi theo locale). */
export const fmtDayMonth = (isoDate: string) =>
  f()
    .dayMonth.formatToParts(new Date(`${isoDate}T00:00:00Z`))
    .filter((part) => part.type === 'day' || part.type === 'month')
    .map((part) => part.value)
    .join('/'); // ICU của vi-VN có bản dùng '-' (Node) có bản dùng '/' (Chrome): tự nối cho đồng nhất

/** Tỉ lệ an toàn: mẫu số 0 thì không có tỉ lệ. */
export const ratio = (part: number, total: number) => (total > 0 ? part / total : null);
