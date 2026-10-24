# 🏷️ ISSUE-006: Sidebar thành ngăn kéo trên màn hẹp và căn hàng form đăng ký model

> **Đích:** `docs/projects/issues/10-2026/ISSUE-006-console-rail-and-form-align/issue.md` · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Done — merge vào develop qua PR (2026-10-24) |
| **Người phụ trách** | HiTranquility (cùng Claude Code) |
| **Phạm vi** | `ai/ui` (chỉ giao diện) |
| **Nhánh** | `feature/ISSUE-006-2026-10-console-rail-and-form-align` |

## Mục tiêu

Hai mục còn lại của [ISSUE-005](../ISSUE-005-console-ui-polish/issue.md), chủ dự án yêu cầu "làm luôn" ngày 2026-10-24:

1. Làm [SUGGESTION-003](../../../suggestions/10-2026/SUGGESTION-003-rail-thu-gon-tren-man-hep.md): dưới 768px, sidebar thành ngăn kéo. Techlead @HiTranquility duyệt trong chat cùng ngày, theo IPLMS ADR-0059.
2. Sửa ô `artifact_key` lệch hàng ở form đăng ký model (ISSUE-004 review-1).

## Tiêu chí chấp nhận

- [x] Dưới 768px:
  - Thanh trên có nút menu (`aria-expanded`, `aria-controls`).
  - Ngăn kéo trượt từ trái, có lớp phủ và nút đóng.
  - Mở ra thì focus vào trong ngăn kéo; Tab vòng trong đó; Esc đóng và trả focus về nút menu.
  - Chuyển trang thì tự đóng; tôn trọng `prefers-reduced-motion`.
- [x] Từ 768px trở lên giữ nguyên sidebar như cũ.
- [x] Các ô của form đăng ký model thẳng hàng; hàng nút ra dòng riêng.
- [x] Không tràn ngang, không chữ dưới AA, không lỗi JS ở 66 màn.

## Đã làm

- `ui/src/components/layout/AppShell.tsx`: thêm thanh trên, ngăn kéo, focus trap, Esc lắng nghe trên `document`, đóng khi đổi route hoặc khi lên màn rộng. `AppShell.module.css`: `@media (max-width: 767px)`.
  - Kiểm trên browser bắt được hai lỗi mà jsdom không thấy:
    - Esc không đóng khi focus chưa vào được ngăn kéo.
    - `visibility` chuyển dần nên khung hình đầu còn `hidden`, focus bị bỏ qua. Đã sửa bằng `visibility 0s` khi mở.
- `ui/src/pages/Vision/ModelsPage.module.css`: `.formGrid` từ `align-items: end` đổi sang `start`. Với `end`, ô có dòng gợi ý (`artifact_key`) bị đẩy input lên 22px. `.testConnRow` chiếm cả dòng.
- `ui/DESIGN.md`: ghi hành vi ngăn kéo. SUGGESTION-003 chuyển 🟢 ACCEPTED.

## Đã kiểm

| Bước | Kết quả |
|---|---|
| `pnpm typecheck`, vitest (thêm `AppShell.test.tsx`), `vite build` | PASS, 18 file / 74 test |
| Playwright ngăn kéo ở 375/768/1280 | 375: `main.top` từ 812 còn 61; mở → focus trong ngăn kéo; Esc → ẩn, focus về nút menu; bấm link → sang trang và đóng. 768/1280: không có nút menu, sidebar như cũ |
| Playwright form đăng ký ở 1280 | 4 input cùng `top` (trước: `artifact_key` lệch 22px) |
| Playwright 66 màn (11 × 375/768/1280 × sáng/tối), có bắt overlay lỗi Vite | 0 tràn ngang, 0 chữ dưới AA, 0 lỗi JS |

## Hồ sơ liên quan

- [SUGGESTION-003](../../../suggestions/10-2026/SUGGESTION-003-rail-thu-gon-tren-man-hep.md) · [ISSUE-005](../ISSUE-005-console-ui-polish/issue.md) · [ISSUE-004 review-1](../ISSUE-004-ai-console-ui-review/review/review-1.md)
