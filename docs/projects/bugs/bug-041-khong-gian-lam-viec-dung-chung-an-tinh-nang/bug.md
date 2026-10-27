# 🐛 bug-041: Không gian làm việc dùng chung giữa tài khoản làm ẩn tính năng; Forecast không có mục menu

> **Đích:** `docs/projects/bugs/bug-041-khong-gian-lam-viec-dung-chung-an-tinh-nang/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed |
| **Người nhận** | @HiTranquility |
| **Hạn** | 2026-10-31 |
| **Ưu tiên** | 🟠 |
| **Ngày đóng** | 2026-10-27 |
| **Người báo** | @HiTranquility ("cái forecast của tui đâu, tính năng này kia đâu hết rồi"); trước đó đã ghi là BUG-04 ở ISSUE-020 review |
| **Ngày báo** | 2026-10-27 |
| **Môi trường** | develop `e732250`, AI Console |

## Hành vi thực tế

1. `ui/src/stores/useWorkspaceStore.ts` lưu không gian đang chọn vào **một** khoá `localStorage` (`iplms_active_workspace`) dùng chung cho mọi tài khoản trên trình duyệt.
2. `AppShell.tsx` và `Home` trong `routes/AuthenticatedRoutes.tsx` lọc menu theo không gian đã lưu, mà không kiểm không gian đó có thuộc tài khoản đang đăng nhập không (chỉ `PersonaSwitcher` có fallback).
3. Hậu quả: Lead hoặc runner demo để ở "Focus Mode" gán nhãn, sau đó một ML engineer đăng nhập thì sidebar gần như trống. Tài khoản chỉ có một không gian còn không có dropdown để đổi lại.
4. `getAvailablePersonas` chia không gian bằng các điều kiện rải rác, gồm cả `me.roles.length >= 3` để được "Tất cả", và cho bất kỳ ai có `ai:metrics:read` vào Copilot Ops.
5. Forecast (`ForecastSimulator`) chỉ nằm trong một tab của "Công cụ thử", không có mục menu riêng nên khó tìm.

## Hành vi mong đợi

- Mỗi tài khoản nhớ không gian riêng. Không gian đã lưu không còn thuộc tài khoản thì dùng không gian đầu tiên của tài khoản đó.
- Không gian chia theo vai bằng một bảng duy nhất, khớp ma trận quyền ở `app/core/console/engines/access_policy.py`.
- Forecast có mục menu "Dự báo & Giá động" trong ML Studio và Copilot Ops.

## Sửa / kiểm chứng

- `useWorkspaceStore.ts`: lưu theo `member_id` (`iplms_active_workspace:<member_id>`); hook nhận `memberId`.
- `navigation.ts`: thêm `ROLE_WORKSPACES` (vai → không gian), `getAvailablePersonas` dựa trên bảng này (từ hai không gian trở lên thì thêm "Tất cả"), và `resolvePersona`. Thêm mục `/forecast` (quyền `ai:metrics:read`, không gian ML Studio và Copilot Ops).
- `AppShell.tsx`, `PersonaSwitcher.tsx`, `AuthenticatedRoutes.tsx`: dùng `resolvePersona`. Thêm route `forecast` và `pages/Forecast/ForecastPage.tsx`, dùng lại `ForecastSimulator`. Tab Forecast trong "Công cụ thử" giữ nguyên.
- i18n VI/EN: `nav.forecast`.
- `ui/DESIGN.md`: mục "Không gian làm việc theo vai".
- Test `PersonaSwitcher.test.tsx`: tài khoản sau không thừa hưởng không gian của tài khoản trước (đỏ trên code cũ, xanh sau sửa); không gian đã lưu không còn hợp lệ thì quay về không gian của tài khoản; bảng chia theo vai.
- `npx tsc --noEmit` ✅; `npx vitest run` 22 file / 103 test ✅; `npx vite build` ✅.
- Chưa soi trên trình duyệt: console đang chạy dùng checkout chính ở nhánh cũ, không phải nhánh này.
