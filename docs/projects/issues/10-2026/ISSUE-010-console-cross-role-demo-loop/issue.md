# 🏷️ ISSUE-010: Kịch Bản & Kiểm Chứng Tự Động Demo Liên Vai I-3 Trên UI AI Console

> **Đích:** `docs/projects/issues/10-2026/ISSUE-010-console-cross-role-demo-loop/issue.md` · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🟢 Resolved (Chờ merge PR) |
| **Người phụ trách** | Dương (@23110012) |
| **Ngày tạo** | 2026-10-25 |
| **Phạm vi** | `ai/ui` (`ui/src/pages/Vision/CrossRoleDemoLoop.test.tsx`, `docs/projects/issues/10-2026/ISSUE-010-console-cross-role-demo-loop/issue.md`) |
| **Liên quan** | IPLMS ISSUE-126 (I-3), IPLMS ADR-0048, SUGGESTION-001, BOARD việc 3 của Dương |

## 🎯 Mục tiêu

Thực hiện hạng mục **Dương 3 (`I-3: demo liên vai trên UI IPLMS-AI bằng iplms-demo-loop`)** trên `BOARD.md`:
1. Đặc tả kịch bản chạy demo liên hoàn qua **5 vai trò nghiệp vụ AI** (`Data Engineer` $\rightarrow$ `Annotator` $\rightarrow$ `Reviewer` $\rightarrow$ `ML Engineer` $\rightarrow$ `AI Lead`) và vai trò quản trị (`Console Admin`).
2. Viết bộ kiểm thử tích hợp tự động (`CrossRoleDemoLoop.test.tsx`) xác nhận toàn bộ hành trình liên vai trên UI:
   - Hiển thị đúng chức năng theo quyền của từng vai trò.
   - Gửi/lưu dữ liệu qua API (`labels`, `decision`, `snapshots`, `propose`, `promote`, `step-up`) chuẩn xác.
   - Chặn truy cập trái phép ở cả tầng điều hướng UI (`App` route guard) lẫn khi API trả lỗi `403 FORBIDDEN` (luật bốn mắt).
3. Ghi nhận rõ điểm chặn ngoài phạm vi khi demo live trên trình duyệt (theo đúng chỉ dẫn trên `BOARD.md`).

---

## 🎬 Kịch bản Demo Liên Vai (I-3 Runbook)

| Bước | Vai trò (`role`) | Màn hình UI | Thao tác thực hiện | Kỳ vọng kết quả & Chốt chặn an toàn |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Annotator**<br>(`ai_annotator`) | `/console/vision/label`<br>(`LabelPage`) | Gán nhãn biển số mẫu đang chờ (`Phím 1` Đúng hoặc sửa biển số + chọn cờ ảnh `two_line`/`glare`). | Gửi `POST /vision/samples/:id/labels`. Nếu truy cập `/console/vision/review` $\rightarrow$ bị chặn *"Vai trò của bạn không mở được mục này"*. |
| **2** | **Reviewer**<br>(`ai_reviewer`) | `/console/vision/review`<br>(`ReviewPage`) | Kiểm tra nhãn do Annotator gán: bấm **Duyệt** (`APPROVED`) hoặc **Trả lại** (`REJECTED` kèm lý do $\ge 3$ ký tự). | Gửi `POST /vision/labels/:id/decision`. Nếu cố tình tự duyệt nhãn của chính mình $\rightarrow$ server trả `403 FORBIDDEN`, UI hiện `role="alert"` và không xóa dòng khỏi hàng đợi. |
| **3** | **Data Engineer**<br>(`ai_data_engineer`) | `/console/vision/datasets`<br>(`DatasetsPage`) | Kiểm tra danh sách mẫu đã duyệt và đóng gói Snapshot (`train` / `golden`). | Hiển thị form tạo Snapshot, nhưng **không có nút Khoá golden** (`canFreeze = false`). |
| **4** | **ML Engineer**<br>(`ai_ml_engineer`) | `/console/vision/models`<br>(`ModelsPage`) | Đăng ký ứng viên model, chạy đo kiểm trên golden đã khoá, và bấm **Đề xuất** (`propose`) kèm lýாக. | Gửi `POST /vision/models/:id/propose` chuyển stage sang `proposed`. **Không có nút Đưa lên production** (`canPromote = false`). |
| **5** | **AI Lead**<br>(`ai_lead`) | `/console/vision/datasets` & `/console/vision/models` | 1) Bấm **Khoá golden** (nhập lý do + mã TOTP step-up 6 số).<br>2) Bấm **Đưa lên production** cho model do ML Engineer đề xuất (kèm TOTP step-up). | - Nếu model do chính AI Lead đó đề xuất $\rightarrow$ nút bị khoá (`"Bạn đề xuất model này — cần AI Lead khác."`).<br>- Nếu do ML Engineer đề xuất $\rightarrow$ qua bước TOTP step-up và promote thành công. |

---

## 🚧 Ghi nhận điểm chặn khi chạy Demo Live ngoài bộ test (Theo quy định BOARD)

1. **Chuyển đổi tài khoản nhanh khi demo trình duyệt:** Sau khi `bug-015` gỡ cửa hậu `/auth/dev-session`, việc chuyển nhanh giữa 5 vai trò trên trình duyệt local mà không cần 5 tài khoản Google OAuth thật đang chờ techlead `@HiTranquility` duyệt [`SUGGESTION-001`](../../suggestions/10-2026/SUGGESTION-001-dang-nhap-dev-cuc-bo-an-toan.md). Trong khi chờ, có thể dùng nút **Nạp 5 mẫu thực hành** ở môi trường dev/sandbox và bộ kiểm thử tự động `CrossRoleDemoLoop.test.tsx`.
2. **Dữ liệu xuất tự động từ kênh A2 Backend:** Kênh worker A2 từ NestJS sang DB `ai_console` thuộc phạm vi tích hợp của `@HiTranquility` (mục `IPLMS ISSUE-126 phase-6 6.3`). Trong phạm vi `IPLMS-AI`, dữ liệu đầu vào được kiểm chứng thông qua fixture cô lập và seed sandbox.

---

## 📋 Tiêu chí chấp nhận

- [x] Có kịch bản rõ ràng cho đủ 5 vai trò nghiệp vụ (`Annotator`, `Reviewer`, `Data Engineer`, `ML Engineer`, `AI Lead`).
- [x] Có test tự động `ui/src/pages/Vision/CrossRoleDemoLoop.test.tsx` kiểm tra xuyên suốt hành trình 5 vai trò, bao gồm cả ca thành công, ca chặn điều hướng sai quyền trên UI, và ca chặn tự duyệt 4 mắt (`403 FORBIDDEN`).
- [x] `tsc --noEmit` và `vitest run` pass 100%.
- [x] `script/check_branch_policy.py` pass 100%.
