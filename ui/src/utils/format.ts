import { currentLang, type Lang } from './lang';

const TZ = 'Asia/Ho_Chi_Minh';
const LOCALE: Record<Lang, string> = { vi: 'vi-VN', en: 'en-US' };
const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 4 });

function build(locale: string) {
  return {
    integer: new Intl.NumberFormat(locale),
    decimal: new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }),
    percent: new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 1 }),
    dateTime: new Intl.DateTimeFormat(locale, { timeZone: TZ, dateStyle: 'short', timeStyle: 'medium' }),
    day: new Intl.DateTimeFormat(locale, { timeZone: 'UTC', weekday: 'short', day: '2-digit', month: '2-digit' }),
  };
}

const cache: Partial<Record<Lang, ReturnType<typeof build>>> = {};
const f = () => (cache[currentLang()] ??= build(LOCALE[currentLang()]));

export const DASH = '—';

export const fmtInt = (n: number | null | undefined) => (n == null ? DASH : f().integer.format(n));
export const fmtMs = (n: number | null | undefined) => (n == null ? DASH : `${f().decimal.format(n)} ms`);
export const fmtPercent = (n: number | null | undefined) => (n == null ? DASH : f().percent.format(n));
export const fmtUsd = (n: number | null | undefined) => (n == null ? DASH : usd.format(n));
export const fmtDateTime = (iso: string) => f().dateTime.format(new Date(iso));
// `date` của chuỗi ngày đã là ngày theo giờ Việt Nam (server gom theo Asia/Ho_Chi_Minh).
export const fmtDay = (isoDate: string) => f().day.format(new Date(`${isoDate}T00:00:00Z`));

/** Tỉ lệ an toàn: mẫu số 0 thì không có tỉ lệ. */
export const ratio = (part: number, total: number) => (total > 0 ? part / total : null);
