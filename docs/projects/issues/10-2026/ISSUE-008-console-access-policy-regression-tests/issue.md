# 🏷️ ISSUE-008: Bổ Sung Test Hồi Quy Ma Trận Quyền 7 Vai Trò AI Console & Chặn API Sai Quyền

> **Đích:** `docs/projects/issues/10-2026/ISSUE-008-console-access-policy-regression-tests/issue.md` · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🟢 Resolved (Chờ merge PR) |
| **Người phụ trách** | Dương (@23110012) |
| **Ngày tạo** | 2026-10-24 |
| **Phạm vi** | `ai` (`app/core/console/engines/access_policy.py`, `app/api/rest/console_access.py`, `test/test_console_access.py`) |
| **Liên quan** | IPLMS ISSUE-126, IPLMS ADR-0048, BOARD việc 4 của Dương |

## 🎯 Mục tiêu

Bổ sung bộ test hồi quy tự động toàn diện kiểm thử ma trận 7 vai trò $\times$ 15 quyền thao tác trên AI Console:
1. Đảm bảo đúng chuẩn phân quyền RBAC (Role-Based Access Control) một nguồn chân lý (`_PERMISSION_ROLES` trong `access_policy.py`).
2. Kiểm tra các ca cho phép (`allow`) và từ chối (`deny`) độc lập đối với từng vai trò (đủ 105 cell ma trận).
3. Kiểm chứng các endpoint REST API được bảo vệ bởi dependency `require_permission` từ chối an toàn với mã lỗi HTTP 403 Forbidden (`FORBIDDEN`) khi token/session thiếu quyền tương ứng, không phụ thuộc vào việc ẩn/hiện nút bấm trên giao diện người dùng.
4. Kiểm thử cơ chế bảo vệ CSRF (`require_same_origin_write`), chốt chặn step-up (`STEP_UP_PERMISSIONS`), và quản lý cookie an toàn (`HttpOnly`, `SameSite=Strict/Lax`).

## 📋 Tiêu chí chấp nhận

- [x] Có ma trận kiểm thử đầy đủ 7 vai trò: `ai_analyst`, `ai_annotator`, `ai_reviewer`, `ai_data_engineer`, `ai_ml_engineer`, `ai_lead`, `ai_console_admin`.
- [x] Kiểm thử toàn bộ 15 quyền hạt nhân (`ai:metrics:read`, `ai:task:label`, `ai:label:approve`, `ai:chatlog:read`, `ai:pii:reveal`, `ai:pipeline:manage`, `ai:dataset:snapshot`, `ai:golden:freeze`, `ai:model:evaluate`, `ai:model:propose`, `ai:model:promote`, `ai:prompt:edit`, `ai:policy:threshold`, `ai:member:manage`, `ai:audit:read`).
- [x] Kiểm thử 105 tổ hợp (7 vai trò $\times$ 15 quyền) với allow/deny hoàn toàn khớp bảng đặc tả chân lý.
- [x] Kiểm thử cơ chế kế thừa/hợp nhất nhiều vai trò (`multiple roles union permissions`).
- [x] Kiểm thử cơ chế tách biệt quyền & đặc quyền tối thiểu: Annotator không được review (nguyên tắc bốn mắt), ML Engineer không được tự promote model lên production, Data Engineer không được sửa prompt.
- [x] Kiểm thử middleware / dependency `require_permission` và `require_any_permission`: trả về HTTP 403 `FORBIDDEN` khi thiếu quyền và HTTP 200 khi đủ quyền.
- [x] Kiểm thử xác thực phiên: trả về HTTP 401 `NO_SESSION` khi thiếu cookie hoặc phiên hết hạn.
- [x] Kiểm thử chống CSRF: chặn unsafe methods (POST) khi thiếu `X-Console-Request: 1` hoặc `Sec-Fetch-Site: cross-site`.
- [x] Bộ test chạy tự động in-memory qua `TestClient`, không phụ thuộc database ngoài và pass 100% (26/26 tests, 0.15s).

## 🛠️ Kết quả thực hiện

- File kiểm thử: `test/test_console_access.py` (26 test cases).
- Đã kiểm tra tính tuân thủ quy tắc nhánh bằng `script/check_branch_policy.py`: PASS.
- Đã kiểm tra biên dịch cú pháp toàn bộ `app` và `test`: PASS.
