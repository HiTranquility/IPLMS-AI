import { csvCell, toCsv } from './csv';

describe('csv', () => {
  it('giữ nguyên số cột khi ô có dấu phẩy', () => {
    expect(toCsv([['Nguyễn, Văn A', 'x']])).toBe('"Nguyễn, Văn A","x"');
  });

  it('chặn công thức ở đầu ô', () => {
    expect(csvCell('=HYPERLINK("http://x","bấm")')).toBe('"\'=HYPERLINK(""http://x"",""bấm"")"');
    for (const c of ['+1', '-1', '@SUM(A1)', '\tx', '\rx']) expect(csvCell(c).startsWith('"\'')).toBe(true);
  });

  it('nhân đôi nháy kép và giữ xuống dòng trong ô', () => {
    expect(csvCell('a "b"\nc')).toBe('"a ""b""\nc"');
  });

  it('ô rỗng và null', () => {
    expect(toCsv([[null, undefined, '']])).toBe('"","",""');
  });
});
