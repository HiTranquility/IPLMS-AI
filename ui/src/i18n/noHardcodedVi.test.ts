import { describe, expect, it } from 'vitest';

// ai bug-023: chữ hiển thị phải đi qua useI18n(). `en: Messages` chỉ bắt thiếu khoá,
// không bắt chữ tiếng Việt viết thẳng trong JSX — test này lấp chỗ đó.
// Vite nạp nguồn thô lúc chạy test; khoá là đường dẫn tương đối kiểu '../pages/X.tsx'.
const SOURCES = import.meta.glob<string>(['../**/*.tsx', '!../**/*.test.tsx', '!../i18n/**', '!../test/**'], {
  query: '?raw',
  import: 'default',
  eager: true,
});
const VI = /[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]/;

// Ngoại lệ có lý do; thêm dòng mới vào đây phải nói rõ vì sao không phải chữ hiển thị.
const ALLOW: { file: string; match: RegExp; why: string }[] = [
  { file: 'components/layout/LanguageSwitch.tsx', match: /Ngôn ngữ · Language/, why: 'nhãn song ngữ cố ý' },
  { file: 'components/common/Ui/data-display/FormattedAnswer.tsx', match: /Nguồn/, why: 'regex khớp trích dẫn trong câu trả lời của model' },
  { file: 'pages/Vision/ReviewPage.tsx', match: /Duyệt nhanh theo lô/, why: 'lý do gửi vào nhật ký kiểm toán phía server' },
  { file: 'pages/Vision/components/LabelForm.tsx', match: /./, why: 'code chết, không được import' },
];

function hardcodedLines(file: string, text: string): string[] {
  const hits: string[] = [];
  let inBlock = false;
  text.split('\n').forEach((line, i) => {
    const s = line.trim();
    if (inBlock) {
      if (s.includes('*/')) inBlock = false;
      return;
    }
    if (s.startsWith('/*') || s.startsWith('{/*')) {
      if (!s.includes('*/')) inBlock = true;
      return;
    }
    if (s.startsWith('//') || s.startsWith('*')) return;
    const code = line.replace(/\{\/\*.*?\*\/\}/g, '').replace(/\/\/.*$/, '');
    if (!VI.test(code)) return;
    if (ALLOW.some((a) => a.file === file && a.match.test(code))) return;
    hits.push(`${file}:${i + 1}: ${s.slice(0, 100)}`);
  });
  return hits;
}

describe('không có chữ tiếng Việt viết thẳng trong TSX (bug-023)', () => {
  it('mọi chữ hiển thị đi qua i18n', () => {
    const files = Object.entries(SOURCES);
    expect(files.length).toBeGreaterThan(50); // glob hỏng thì không được xanh giả
    const hits = files.flatMap(([path, text]) => hardcodedLines(path.replace(/^\.\.\//, ''), text));
    expect(hits).toEqual([]);
  });
});
