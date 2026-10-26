# 🐛 bug-019: Xuất CSV nhật ký audit không escape: vỡ cột và dính formula injection

> **Đích:** `docs/projects/bugs/bug-019-audit-xuat-csv-khong-escape/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code, rà UI trong [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) |
| **Trạng thái** | ✅ Fixed — merge vào develop qua HiTranquility/IPLMS-AI#52 (2026-10-24) / 🟠 bảo mật mức vừa |
| **Ngày đóng** | 2026-10-24 |
| **Ưu tiên** | 🟠 |
| **Môi trường** | `develop@5f8e753` |

## Hành vi thực tế

Nút "Xuất CSV" ở trang Nhật ký ghép từng dòng bằng `[...].join(',')`. Chỉ cột `reason` được bọc nháy kép. Các cột khác do người dùng nhập (tên hiển thị khi mời thành viên, `target_id`) thì đi thẳng vào file:

- Tên có dấu phẩy (ví dụ "Nguyễn, Văn A") làm lệch toàn bộ cột phía sau.
- Lý do hoặc tên bắt đầu bằng `=`, `+`, `-`, `@` sẽ bị Excel hoặc Sheets coi là công thức (CSV/formula injection, OWASP). Lý do là trường tự do 3-500 ký tự mà mọi vai có quyền ghi đều nhập được.
- Tiêu đề cột và nhãn hành động luôn là tiếng Việt, kể cả khi đang dùng EN.

## Hành vi mong đợi

Mọi ô được bọc nháy kép và nhân đôi nháy bên trong. Ô bắt đầu bằng `= + - @ \t \r` được thêm tiền tố `'`. Tiêu đề cột theo ngôn ngữ đang chọn. Nên có test cho ca có dấu phẩy và ca bắt đầu bằng `=`.

## Tái hiện

Đọc `ui/src/pages/Audit/AuditPage.tsx:96-123`. Muốn thử trên UI: mời một thành viên tên `=HYPERLINK("http://x","bấm")`, cấp vai trò, rồi xuất CSV và mở bằng Excel.

## Bằng chứng

- `ui/src/pages/Audit/AuditPage.tsx:100-113`: chỉ `reason` được quote (dòng 112).
- Ảnh trang: `../../issues/10-2026/ISSUE-004-ai-console-ui-review/evidence/06-audit.png`.

## Sửa / kiểm chứng

Đã sửa trên nhánh `bugfix/bug-019-2026-10-audit-export-and-actions` (2026-10-24):

- `ui/src/utils/csv.ts`: `csvCell` bọc nháy mọi ô, nhân đôi nháy bên trong, thêm tiền tố `'` cho ô mở đầu bằng `= + - @ \t \r`; `toCsv` ghép dòng bằng `\r\n`.
- `ui/src/pages/Audit/AuditPage.tsx:105,116`: xuất CSV qua `toCsv`; cột hành động dùng nhãn theo ngôn ngữ (`actionLabel`), người làm trống ghi `t.audit.system`.
- Tiêu đề cột theo ngôn ngữ: `ui/src/i18n/vi.ts:573`, `ui/src/i18n/en.ts:595` (`audit.csvHeaders`).

Kiểm chứng:

- `ui/src/utils/csv.test.ts`: ô có dấu phẩy, ô mở đầu `=HYPERLINK(...)`, các ký tự `+ - @ \t \r`, nháy kép và xuống dòng, ô rỗng/null.
- `pnpm typecheck` PASS; `npx vitest run --maxWorkers=1` PASS 14 file / 56 test.
- Chưa mở file xuất bằng Excel/Sheets thật (không có trên môi trường kiểm).
