# 🐛 bug-019: Xuất CSV nhật ký audit không escape: vỡ cột và dính formula injection

> **Đích:** `docs/projects/bugs/bug-019-audit-xuat-csv-khong-escape/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code, rà UI trong [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) |
| **Trạng thái** | 🆕 New / 🟠 bảo mật mức vừa |
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

Chưa sửa.
