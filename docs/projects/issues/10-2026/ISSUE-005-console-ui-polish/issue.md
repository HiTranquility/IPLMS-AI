# 🏷️ ISSUE-005: Chỉnh UI AI Console theo các mục "nên thêm / nên bớt" của lượt rà ISSUE-004

> **Đích:** `docs/projects/issues/10-2026/ISSUE-005-console-ui-polish/issue.md` · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🚧 In progress |
| **Người phụ trách** | HiTranquility (cùng Claude Code), theo yêu cầu chủ dự án ngày 2026-10-24 |
| **Phạm vi** | `ai/ui` (chỉ giao diện, không đổi API/schema) |
| **Nhánh** | `feature/ISSUE-005-2026-10-console-ui-polish`, tách từ `bugfix/bug-021-2026-10-console-ui-polish`, nên merge sau nhánh đó |

## Mục tiêu

Nguyên văn yêu cầu: "sửa rồi sau đó làm thêm chỉnh UI này kia là đc". Làm các mục chỉnh UI đã ghi trong [ISSUE-004 review-1](../ISSUE-004-ai-console-ui-review/review/review-1.md) (§Đánh giá UI/UX, §Độ khớp, §Nên thêm/nên bớt). Không gồm các mục cần techlead duyệt trước.

## Tiêu chí chấp nhận

- [ ] Màu viết thẳng trong `*.module.css` đưa về token (`ui/DESIGN.md` §Luật 8). Riêng bảng màu vai/hành động là bảng màu định danh có chủ đích: gom thành token riêng, không để hex rải rác.
- [ ] Trang đăng nhập bỏ nền sao động, gradient và quầng sáng (`ui/DESIGN.md` §Luật 3).
- [ ] Gỡ thẻ "Quy chuẩn kiến trúc" tĩnh ở Công cụ thử (review-1 S7).
- [ ] Ngày giờ dễ quét: Copilot Lab hiện ngày trước giờ; ngày mời thành viên không kèm giây.
- [ ] Các lỗi nhỏ review-1 đã ghi: nút "Phân vai trò" xuống dòng, ID mẫu bị cắt không xem được bản đầy đủ, ảnh lỗi thiếu chữ thay thế, ô `artifact_key` lệch hàng.
- [ ] Kiểm: `pnpm typecheck`, vitest, Playwright 11 màn × 375/768/1280 × sáng/tối không tràn ngang, không chữ dưới AA, không lỗi JS.

## Ngoài phạm vi (chờ duyệt)

- Sidebar thu gọn trên màn hẹp: [SUGGESTION-003](../../../suggestions/10-2026/SUGGESTION-003-rail-thu-gon-tren-man-hep.md) đang 🔄 REVIEWING (IPLMS ADR-0056: chỉ merge khi techlead ACCEPTED).
- Gỡ mount `/api` trùng của console (đổi bề mặt API), ghi ở review-1 S7.

## Hồ sơ liên quan

- [ISSUE-004](../ISSUE-004-ai-console-ui-review/issue.md) · [review-1](../ISSUE-004-ai-console-ui-review/review/review-1.md) · [review-2](../ISSUE-004-ai-console-ui-review/review/review-2.md)
