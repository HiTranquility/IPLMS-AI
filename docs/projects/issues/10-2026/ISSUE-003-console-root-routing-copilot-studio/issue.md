# 🏷️ ISSUE-003: Định tuyến trực tiếp Root URL và Nâng cấp Copilot Chat Studio 3-Panel

> **Đích:** `docs/projects/issues/10-2026/ISSUE-003-console-root-routing-copilot-studio/issue.md`

| | |
|---|---|
| **Trạng thái** | 🚧 In progress |
| **Ngày tạo** | 2026-10-22 |
| **Người phụ trách** | AI Team & HiTranquility |
| **Phạm vi** | `ai/` (`app/console_main.py`, `ui/`, `app/api/rest/routes/console_tools_controller.py`) |

## Bối cảnh & Mục tiêu

Giao diện AI Console nội bộ (`ai/ui`) trước đây bị ép buộc tiền tố `/console/` trên URL khiến trải nghiệm điều hướng rườm rà. Đồng thời, khu vực Copilot chỉ có trang duyệt và chấm điểm nhật ký quá khứ (Review Lab), thiếu một không gian Chat tương tác đa năng chuyên nghiệp để nhân viên vận hành và chuyên gia AI có thể hỏi đáp quy chế bãi xe theo thời gian thực (RAG streaming) kèm kiểm tra viễn trắc và trích dẫn.

Mục tiêu của ISSUE-003:
1. **Định tuyến Root URL linh hoạt:** Hỗ trợ truy cập trực tiếp `http://localhost:8095/` lẫn tiền tố `/console/` tương thích ngược 100%, đồng thời giữ nguyên CSP `default-src 'self'` nghiêm ngặt theo ADR-0048.
2. **Copilot Chat Studio 3-Panel:** Xây dựng workspace tương tác 3 cột chuẩn Hallmark:
   - Cột trái: Danh mục câu hỏi mẫu quy chế (Presets) & quản lý hội thoại.
   - Cột giữa: Khung chat streaming SSE thời gian thực, hiển thị trích dẫn RAG, hỗ trợ phím tắt, copy và phản hồi nhanh.
   - Cột phải: Ngăn kéo kiểm định (Inspector Drawer) hiển thị Citations tài liệu, Telemetry thực thi (độ trễ, số lượng token, tốc độ tokens/s, mức dùng ngữ cảnh) và bảng điều khiển tham số mô hình (Playground Parameters).
3. **Phân rã Component & Tuân thủ Hallmark:** Phân rã giao diện thành các sub-components chuẩn `PAT-006` và `ai/ui/DESIGN.md`, 100% token CSS, 0 pixel cứng, 0 emoji, bảo đảm 100% test suite xanh.

## Tiêu chí chấp nhận

- [x] Truy cập `http://localhost:8095/` phục vụ trực tiếp SPA tại root mà không bị chuyển hướng cưỡng bức sang `/console/`.
- [x] API hỗ trợ cả `/api` và `/console/api`, giữ nguyên cookie auth `SameSite=Strict` và header `X-Console-Request: 1`.
- [x] Giao diện Copilot Lab hỗ trợ chuyển đổi linh hoạt giữa `Chat Studio` và `Review Lab` qua Segmented control. Mặc định `viewMode = 'review'` để bảo đảm tính tương thích với các bài kiểm thử hiện hữu.
- [x] Tích hợp đầy đủ streaming SSE từ `/tools/copilot/stream`, hiển thị từng chunk token theo thời gian thực, có nút dừng stream (`AbortController`).
- [x] Tính năng UX nâng cao: Copy câu trả lời vào clipboard, phản hồi nhanh Thích/Không thích (tương thích review log), xuất hội thoại dạng Markdown, phím tắt `Ctrl+Enter` gửi tin và `Escape` đóng drawer.
- [x] Tuân thủ 8 quy tắc Hallmark Design System: Không emoji làm icon, không fake metrics, không gradient/glow/box-shadow, không hardcode `px`, dùng font hệ thống và token Graphite & Amber.
- [x] 100% test suite pass: `pnpm test` (25/25 tests PASS), `pnpm build` pass, `python -m unittest` pass.

## Hồ sơ liên quan

- ADR-0048: AI Console nội bộ trong khối `ai/`
- ADR-0049: Telemetry AI lưu ở `ai-db`
- ADR-0052: Convention audit độc lập trước commit
- ISSUE-126: AI Console nội bộ
