# 🌱 SUGGESTION-007: Thêm Helper Text Lý Do Trả Lại Nhãn và Bộ Chuyển Đổi Vai Trò Nhanh Trên Môi Trường Dev

> **Đích:** `docs/projects/suggestions/10-2026/SUGGESTION-007-helper-text-ly-do-tra-lai-nhan-va-role-quick-switch.md` · **Luật chung:** [templates/README](../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 💡 DRAFT |
| **Người nhận** | @HiTranquility |
| **Hạn** | 2026-10-31 |
| **Ưu tiên** | 🟢 |
| **Ngày đóng** | — |
| **Ngày** | 2026-10-26 |
| **Người đề xuất** | Antigravity Pair Programming (Quan sát qua Browser Testing) |
| **Techlead duyệt** | @HiTranquility — ⏳ chờ |
| **Làm trước khi duyệt?** | Không |
| **Phạm vi** | `ai/ui` (AI Console UI) |

---

## Đề xuất

Trong quá trình chạy giả lập hành vi người dùng bằng Browser Control, phát hiện 2 điểm "sạn" về mặt trải nghiệm người dùng (UX) và đề xuất cải thiện:

### Đề xuất 1: Thêm dòng Helper Text hướng dẫn khi từ chối nhãn (`/vision/review`)
- **Hiện trạng:** Khi Reviewer bấm *"Trả lại…"*, một cửa sổ bật lên yêu cầu nhập lý do. Hệ thống có luật nghiệp vụ bắt buộc lý do từ chối phải $\ge 3$ ký tự. Nếu người dùng chỉ gõ 1–2 ký tự (`"ko"`, `"sai"`), nút *"Xác nhận trả lại"* bị vô hiệu hóa (`disabled`) nhưng **không có dòng giải thích lý do tại sao nút bị khóa**.
- **Đề xuất:** Bổ sung dòng gợi ý dưới ô nhập:
  - Khi chưa đủ 3 ký tự: Hiển thị chữ màu phụ kèm số đếm ký tự: `"Vui lòng nhập lý do tối thiểu 3 ký tự (còn thiếu X ký tự)"`.
  - Khi đủ $\ge 3$ ký tự: Chuyển sang thông báo hợp lệ hoặc ẩn đi.

### Đề xuất 2: Bổ sung thanh chuyển đổi nhanh giữa các vai trò (Dev Role Quick-Switch)
- **Hiện trạng:** Khi demo hoặc audit thử nghiệm tại local, người kiểm thử phải liên tục: Đăng xuất $\rightarrow$ Mở dropdown mật khẩu khẩn cấp $\rightarrow$ Gõ email $\rightarrow$ Gõ mật khẩu $\rightarrow$ Mở app lấy OTP $\rightarrow$ Điền OTP để chuyển từ Annotator sang Reviewer sang Lead. Việc này mất nhiều thời gian và gây ngắt quãng luồng demo.
- **Đề xuất:** Khi chạy ở chế độ dev (`APP_ENV=development` và `AI_CONSOLE_DEMO_SEED_ENABLED=true`), thêm một thanh chọn nhanh vai trò (Role Switcher bar hoặc Dropdown góc dưới) cho phép chuyển đổi phiên đăng nhập giữa 6 tài khoản mẫu chỉ với 1-click (đối chiếu `SUGGESTION-001`).

---

## Vấn đề nó giải quyết

1. **Giảm cảm giác bối rối (Confusion):** Người dùng lần đầu tiên trải nghiệm giao diện không bị cảm giác "tại sao tôi bấm nút không ăn / bị đơ".
2. **Tăng tốc độ Demo & Audit:** Giúp các bên thứ ba tham gia audit hệ thống (theo `ISSUE-020`) thử nghiệm chuỗi liên vai 4-mắt trơn tru, liền mạch.

---

## Phạm vi

- **Trong phạm vi:**
  - Component `ReviewPage.tsx` / modal từ chối nhãn.
  - Component `DevRoleSwitcher.tsx` (chỉ mount khi biến môi trường dev cho phép).
- **Ngoài phạm vi:** Không thay đổi logic backend hay chính sách bảo mật production.

---

## Bằng chứng / tham khảo

- Ghi nhận trong phiên test Playwright tại `ai/docs/projects/issues/10-2026/ISSUE-020-ke-hoach-demo-audit-ai-console/handoff/phieu-audit-1.md`.
- File liên quan: `ai/ui/src/pages/Vision/ReviewPage.tsx`.

---

## Bước tiếp theo

Chờ Techlead `@HiTranquility` xem xét và duyệt trước khi tạo issue triển khai UI.
