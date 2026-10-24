# 🐛 bug-023: Chuyển sang EN thì phần lớn màn hình vẫn là tiếng Việt (419 dòng viết cứng trong 47 file)

> **Đích:** `docs/projects/bugs/bug-023-che-do-en-tron-tieng-viet/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code, rà UI trong [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) |
| **Trạng thái** | 🆕 New / 🟡 (cổng chất lượng L6 không đạt) |
| **Môi trường** | `develop@5f8e753` |

## Hành vi thực tế

Bấm EN ở `/vision/label`: tiêu đề và mô tả đổi sang tiếng Anh, nhưng phần còn lại vẫn tiếng Việt: "HÀNG ĐỢI A2", "Nạp 5 mẫu thực hành", "Lịch sử", "Ảnh cắt từ camera cổng", "MÁY NHẬN DIỆN (AI)", "THUỘC TÍNH ẢNH / BIỂN SỐ", "Đúng 100%", "Sửa biển", "Ảnh hỏng" và cả dải phím tắt. Trang đăng nhập cũng vậy: "Truy cập nhanh…", "HOẶC TÀI KHOẢN KHẨN CẤP", "Xác thực an toàn qua OAuth 2.0 PKCE…". Bảng ở mục Bằng chứng cho thấy lỗi có ở hầu hết phần thêm sau P6.

`ui/DESIGN.md` §Ngôn ngữ nói `en.ts` khai `en: Messages` để `tsc` bắt thiếu khoá. Cơ chế này chỉ bắt được khoá thiếu trong từ điển, không bắt được chữ viết thẳng trong JSX, nên typecheck vẫn xanh.

## Hành vi mong đợi

Theo quality-gate L6 (IPLMS ADR-0041): đổi VI↔EN không sót chuỗi. Chữ hiển thị đều đi qua `useI18n()`. Nên thêm kiểm tự động, ví dụ quét chữ có dấu tiếng Việt trong `*.tsx` ngoài `i18n/` và test.

## Tái hiện

1. `pnpm --dir ui dev` cùng một API giả (`evidence/mock_console_api.py`), mở `/vision/label`, bấm EN.
2. `document.querySelector('main').innerText` → phần lớn vẫn tiếng Việt (kiểm bằng browser pane ngày 2026-10-23).

## Bằng chứng

Đếm dòng có chữ tiếng Việt có dấu trong `ui/src/**/*.tsx` (bỏ comment, bỏ test): **419 dòng / 47 file**. Nhiều nhất:

| File | Dòng |
|---|---|
| `pages/Vision/components/AnprSandbox/AnprSandbox.tsx` | 56 |
| `pages/Copilot/components/ChatStudio/KnowledgeExplorer.tsx` | 42 |
| `pages/Copilot/components/ChatStudio/DisputeSimulator.tsx` | 38 |
| `pages/Vision/components/LabelStudio/LabelWorkspace.tsx` | 30 |
| `pages/Vision/components/LabelStudio/LabelEmptyStudio.tsx` | 24 |
| `pages/Copilot/components/ChatStudio/ChatStudio.tsx` | 22 |
| `pages/Vision/ReviewPage.tsx` | 17 |

Có thể có vài dòng là chuỗi trong log hoặc thông báo lỗi; con số dùng để ước độ lớn việc, không phải danh sách chính xác.

## Sửa / kiểm chứng

Chưa sửa.
