/** CSV an toàn cho Excel/Sheets: mọi ô bọc nháy kép, nháy bên trong nhân đôi, ô mở đầu bằng
 *  ký tự công thức (= + - @ tab CR) thêm tiền tố `'` để không bị chạy như công thức (OWASP CSV injection). */
const FORMULA_START = /^[=+\-@\t\r]/;

export function csvCell(value: unknown): string {
  let text = value == null ? '' : String(value);
  if (FORMULA_START.test(text)) text = `'${text}`;
  return `"${text.replace(/"/g, '""')}"`;
}

export function toCsv(rows: unknown[][]): string {
  return rows.map((row) => row.map(csvCell).join(',')).join('\r\n');
}
