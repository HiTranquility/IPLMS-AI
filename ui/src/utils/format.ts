const TZ = 'Asia/Ho_Chi_Minh';
const integer = new Intl.NumberFormat('vi-VN');
const decimal = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 });
const percent = new Intl.NumberFormat('vi-VN', { style: 'percent', maximumFractionDigits: 1 });
const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 4 });
const dateTime = new Intl.DateTimeFormat('vi-VN', { timeZone: TZ, dateStyle: 'short', timeStyle: 'medium' });
const day = new Intl.DateTimeFormat('vi-VN', { timeZone: 'UTC', weekday: 'short', day: '2-digit', month: '2-digit' });

export const DASH = '—';

export const fmtInt = (n: number | null | undefined) => (n == null ? DASH : integer.format(n));
export const fmtMs = (n: number | null | undefined) => (n == null ? DASH : `${decimal.format(n)} ms`);
export const fmtPercent = (n: number | null | undefined) => (n == null ? DASH : percent.format(n));
export const fmtUsd = (n: number | null | undefined) => (n == null ? DASH : usd.format(n));
export const fmtDateTime = (iso: string) => dateTime.format(new Date(iso));
// `date` của chuỗi ngày đã là ngày theo giờ Việt Nam (server gom theo Asia/Ho_Chi_Minh).
export const fmtDay = (isoDate: string) => day.format(new Date(`${isoDate}T00:00:00Z`));

/** Tỉ lệ an toàn: mẫu số 0 thì không có tỉ lệ. */
export const ratio = (part: number, total: number) => (total > 0 ? part / total : null);
