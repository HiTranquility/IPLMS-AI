# 🏷️ ISSUE-005: Chỉnh UI AI Console theo các mục "nên thêm / nên bớt" của lượt rà ISSUE-004

> **Đích:** `docs/projects/issues/10-2026/ISSUE-005-console-ui-polish/issue.md` · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Done — merge vào develop qua PR (2026-10-24) |
| **Ngày đóng** | 2026-10-24 |
| **Người phụ trách** | HiTranquility (cùng Claude Code), theo yêu cầu chủ dự án ngày 2026-10-24 |
| **Phạm vi** | `ai/ui` (chỉ giao diện, không đổi API/schema) |
| **Nhánh** | `feature/ISSUE-005-2026-10-console-ui-polish`, tách từ `bugfix/bug-021-2026-10-console-ui-polish`, nên merge sau nhánh đó |

## Mục tiêu

Nguyên văn yêu cầu: "sửa rồi sau đó làm thêm chỉnh UI này kia là đc". Làm các mục chỉnh UI đã ghi trong [ISSUE-004 review-1](../ISSUE-004-ai-console-ui-review/review/review-1.md) (§Đánh giá UI/UX, §Độ khớp, §Nên thêm/nên bớt). Không gồm các mục cần techlead duyệt trước.

## Tiêu chí chấp nhận (Definition of Done / Acceptance Criteria)

- [x] Màu viết thẳng trong `*.module.css` đưa về token (`ui/DESIGN.md` §Luật 8). Riêng bảng màu vai/hành động là bảng màu định danh có chủ đích: gom thành token riêng, không để hex rải rác.
- [x] Trang đăng nhập bỏ nền sao động, gradient và quầng sáng (`ui/DESIGN.md` §Luật 3).
- [x] Gỡ thẻ "Quy chuẩn kiến trúc" tĩnh ở Công cụ thử (review-1 S7).
- [x] Ngày giờ dễ quét: Copilot Lab hiện ngày trước giờ; ngày mời thành viên không kèm giây.
- [x] Các lỗi nhỏ review-1 đã ghi: nút "Phân vai trò" xuống dòng, ID mẫu bị cắt không xem được bản đầy đủ, ảnh lỗi thiếu chữ thay thế, ô `artifact_key` lệch hàng.
- [x] Kiểm: `pnpm typecheck`, vitest, Playwright 11 màn × 375/768/1280 × sáng/tối không tràn ngang, không chữ dưới AA, không lỗi JS.

## Đã làm (2026-10-24)

- **Token:** thêm `--shadow-sm|md|lg`, `--color-scrim`, `--color-viewer-*` (`ui/src/index.css`). Thay 41 đổ bóng/lớp phủ/màu viết thẳng, cùng nền menu PersonaSwitcher, chip trích dẫn ở FormattedAnswer, badge ChatStudio, khung soi ảnh LabelPage. Chỉ còn ba ngoại lệ có chủ đích, đã ghi ở `ui/DESIGN.md` §Luật 8: nút/logo Google, bảng màu vai (`RoleBadge`), bảng màu nhóm hành động (`AuditActionBadge`).
- **Token không tồn tại** (biến rỗng nên CSS bị bỏ qua): `--color-surface-hover`, `--radius-xl`, `--text-base`, `--text-2xl`, đã đổi sang token có thật.
- **Không gradient/glow/animation trang trí** (§Luật 3): xoá `EnterpriseBackground` (canvas sao động + radial gradient, 274 dòng) khỏi trang đăng nhập và MFA; panel phẳng `--color-surface` + hairline; bỏ gradient avatar ở Thành viên, nhịp pulse ở Model đang phục vụ.
- **Không `transition: all`** (§Luật 4): 12 chỗ đổi sang danh sách thuộc tính cụ thể.
- **Công cụ thử:** gỡ thẻ "Quy chuẩn kiến trúc" tĩnh, cùng 9 khoá i18n và CSS chỉ nó dùng. Mô tả trang sửa cho khớp; nút "Làm mới" không xuống dòng.
- **Ngày giờ:** `fmtDateTime` cho ra `dd/mm/yy hh:mm` (vi) / `mm/dd/yy hh:mm` (en), ngày trước giờ, bỏ giây (`ui/src/utils/format.ts`), có test.
- **Lỗi nhỏ:**
  - Nút "Phân vai trò" không xuống dòng.
  - ID mẫu có `title` hiện mã đầy đủ.
  - Ảnh lỗi có chữ "Không tải được ảnh cắt", ô lỗi không co thành dải hẹp.
  - Duyệt nhãn: "cổng xác nhận" trống thì hiện "— (chưa có)" kèm giải thích.
  - Lưới Gán nhãn dùng `minmax(0, …)`, không còn tràn ngang.

## Đã kiểm

| Bước | Kết quả |
|---|---|
| `pnpm typecheck` | PASS |
| `npx vitest run --maxWorkers=1` | 17 file / 72 test PASS |
| `npx vite build` (ra scratchpad) | PASS. Bước này bắt được một lỗi cú pháp CSS mà typecheck/vitest bỏ sót. Đã chạy cho cả 4 nhánh bug: đều PASS |
| Playwright 11 màn × 375/768/1280 × sáng/tối = 66 màn, có bắt overlay lỗi Vite | 0 tràn ngang, 0 chữ dưới AA, 0 lỗi JS |
| Soát ảnh bằng mắt: đăng nhập, Gán nhãn, Công cụ thử | Đạt |

Ô `artifact_key` lệch hàng và sidebar màn hẹp: đã làm ở [ISSUE-006](../ISSUE-006-console-rail-and-form-align/issue.md). Lỗi lệch hàng tái hiện được trên API giả; lần trước chỉ chưa đo tới form này.

## Ngoài phạm vi (chờ duyệt)

- Sidebar thu gọn trên màn hẹp: [SUGGESTION-003](../../../suggestions/10-2026/SUGGESTION-003-rail-thu-gon-tren-man-hep.md) đang 🔄 REVIEWING (IPLMS ADR-0059: chỉ merge khi techlead ACCEPTED).
- Gỡ mount `/api` trùng của console (đổi bề mặt API), ghi ở review-1 S7.

## Hồ sơ liên quan

- [ISSUE-004](../ISSUE-004-ai-console-ui-review/issue.md) · [review-1](../ISSUE-004-ai-console-ui-review/review/review-1.md) · [review-2](../ISSUE-004-ai-console-ui-review/review/review-2.md)
