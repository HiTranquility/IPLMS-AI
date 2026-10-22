# 🛡️ AUDIT-005: Rà Soát Bảo Mật Toàn Diện AI Console (Security Review Gate I-2)

> **Đích:** `docs/projects/audits/10-2026/AUDIT-005-ai-console-security-review.md` · **Luật chung:** [templates/README](../../../templates/README.md)  
> **Nguồn gốc:** Nghiệm thu đầu việc HiTranquility #5 (Gate I-2 theo [IPLMS ISSUE-126](../../issues/10-2026/ISSUE-126-ai-console-noi-bo/issue.md), [ADR-0048](../../adrs/10-2026/0048-ai-console-noi-bo-trong-khoi-ai.md), [ADR-0051](../../adrs/10-2026/0051-backend-keo-nguong-anpr-da-duyet-tu-ai-console-qua-rpc.md)).

## 📌 Meta

| | |
|---|---|
| **ID** | AUDIT-005 |
| **Trạng thái** | ✅ Đóng (0 vi phạm còn lại — Passed Security Gate) |
| **Ngày rà soát** | 2026-10-22 |
| **Người thực hiện** | HiTranquility (TechLead / M1 Owner) |
| **Phạm vi (Scope)** | `ai/app/core/console/**`, `ai/app/infra/database/**`, `ai/app/infra/identity/**`, `ai/ui/**` |
| **Quy ước đối chiếu** | [ADR-0048](../../adrs/10-2026/0048-ai-console-noi-bo-trong-khoi-ai.md), [ADR-0051](../../adrs/10-2026/0051-backend-keo-nguong-anpr-da-duyet-tu-ai-console-qua-rpc.md), OWASP ASVS v4.0.3 (Authentication & Access Control) |
| **Tags** | `security`, `rbac`, `audit`, `least-privilege`, `totp`, `ai-console` |

---

## 1. Luật gốc đối chiếu (Rules under audit)

1. **[MUST] Phân quyền đa vai (ADR-0048 §4):** Kiểm tra 7 vai trò nội bộ (`ai_annotator`, `ai_reviewer`, `ai_analyst`, `ai_data_engineer`, `ai_ml_engineer`, `ai_lead`, `ai_console_admin`), ánh xạ nghiêm ngặt 15 quyền nghiệp vụ. Không mượn quyền từ Admin/Moderator của platform.
2. **[MUST] Xác thực & Chống Brute-force (OWASP / ADR-0048 §2):** Bắt buộc Google OAuth2 OIDC + MFA TOTP (RFC 6238). Khóa phiên sau tối đa 5 lần thử sai mã TOTP (`TOO_MANY_ATTEMPTS`). Khóa 15 phút nếu nhập sai mật khẩu khẩn cấp 5 lần.
3. **[MUST] Bất biến Nhật ký Kiểm toán (ADR-0048 §3):** Bảng `audit_event` lưu vết mọi thay đổi trạng thái trong CÙNG transaction. Trigger Postgres cấm tuyệt đối thao tác `UPDATE`, `DELETE`, `TRUNCATE`.
4. **[MUST] Quyền tối thiểu của Process Inference (ADR-0051 §6):** Process inference (`app.grpc_server`) chỉ được kết nối DB console bằng role `ai_inference`, giới hạn duy nhất ở các bảng kênh A2 (`vision_sample`, `vision_crop`, `vision_import_cursor`, `vision_import_error`) và `SELECT` bảng `accept_policy`. Bị CHẶN truy cập toàn bộ bảng quản trị và tài khoản thành viên.
5. **[MUST] Bảo vệ Dữ liệu Định danh & PII (ADR-0048 §5, ADR-0049):** Không log PII dạng rõ (biển số xe, tên người dùng). User ID trong telemetry được băm HMAC SHA256; ảnh cắt A2 chưa gán nhãn tự động xóa sau 90 ngày.

---

## 2. Phương pháp kiểm chứng (Reproducible Method)

```bash
# 1. Kiểm tra ma trận 7 vai trò ~ 15 quyền và luồng xác thực Google + TOTP
python -m unittest test.test_console_access test.test_console_auth -v

# 2. Kiểm chứng phân quyền tối thiểu (Least Privilege) role ai_inference trên Postgres
python -m unittest test.test_console_db_hardening -v
python -m app.script.harden_console_db --verify-only

# 3. Kiểm chứng trigger cấm sửa/xóa audit_event
python -m unittest test.test_console_http -v
```

* **Số ca kiểm thử đã thực thi:** 58 tests bảo mật tập trung (100% PASS).
* **Kiểm tra trực tiếp trên Postgres:** Role `ai_inference` bị chặn với `Permission Denied` khi truy cập `console_member` và `audit_event`.

---

## 3. Kết quả đánh giá chi tiết (Findings & Remediation)

### ✅ Nhóm A — Các lỗ hổng đã được phát hiện và khắc phục triệt để

| # | Vị trí (`file:line`) | Nguy cơ / Hiện trạng ban đầu | Hành động khắc phục đã thực hiện | Trạng thái |
|---|---|---|---|---|
| A1 | [`app/core/console/services/auth_service.py`](file:///C:/Users/Admin/Downloads/IPLMS/ai/app/core/console/services/auth_service.py) | **Thiếu Rate Limiting TOTP:** Cho phép brute-force vét cạn 1.000.000 hoán vị mã OTP 6 số | Bổ sung đếm `totp_attempts`. Hủy phiên ngay lập tức khi sai 5 lần (`TOO_MANY_ATTEMPTS`) và ghi audit log | ✅ Resolved |
| A2 | [`docker/database-vector/init/11-ai-inference-role.sh`](file:///C:/Users/Admin/Downloads/IPLMS/ai/docker/database-vector/init/11-ai-inference-role.sh) | **Process Inference sở hữu toàn quyền DB:** Dùng chung tài khoản `ai_console` có quyền sửa đổi thành viên và xóa dữ liệu | Tạo role riêng `ai_inference`, thu hồi toàn bộ quyền bảng nhạy cảm, chỉ mở bảng A2 và đọc `accept_policy` | ✅ Resolved |
| A3 | [`app/script/compile_proto.py`](file:///C:/Users/Admin/Downloads/IPLMS/ai/app/script/compile_proto.py) | **Lệch Schema Protobuf (BUG-06):** Script đọc stub cục bộ trong `ai/proto` trước monorepo root | Đảo thứ tự ưu tiên: đọc `REPO_ROOT / proto` trước `AI_ROOT / proto` để tránh lệch hợp đồng RPC với NestJS | ✅ Resolved |
| A4 | [`app/api/grpc/mappers/copilot_mapper.py`](file:///C:/Users/Admin/Downloads/IPLMS/ai/app/api/grpc/mappers/copilot_mapper.py) | **Lỗi DTO Telemetry Crash RPC:** `avg_speed_tok_s` chưa khai báo trong proto làm sập handler | Loại trừ các trường telemetry giao diện (`avg_speed_tok_s`, `speed_tok_s`) khi đóng gói protobuf response | ✅ Resolved |

### 🛡️ Nhóm B — Các chốt kiểm soát an toàn đã nghiệm thu (Approved Controls)

| Mục kiểm soát | Thành phần thực thi | Bằng chứng kiểm chứng |
|---|---|---|
| **Ma trận 7 vai trò** | [`access_policy.py`](file:///C:/Users/Admin/Downloads/IPLMS/ai/app/core/console/engines/access_policy.py) | 15/15 quyền được kiểm tra `allow/deny` đầy đủ trong `test_console_access.py` |
| **Mã hóa khóa TOTP** | [`console_store.py`](file:///C:/Users/Admin/Downloads/IPLMS/ai/app/infra/database/console_store.py) | Bí mật TOTP được mã hóa đối xứng AES bằng Fernet key (`totp_encryption_key`) |
| **Bảo vệ Cookie phiên** | [`auth_service.py`](file:///C:/Users/Admin/Downloads/IPLMS/ai/app/core/console/services/auth_service.py) | Cookie `console_session` gắn cờ `HttpOnly`, `SameSite=Lax`, thời hạn 8 giờ và idle timeout 30 phút |
| **Chống can thiệp Audit** | [`console_store.py:165`](file:///C:/Users/Admin/Downloads/IPLMS/ai/app/infra/database/console_store.py) | Trigger `audit_event_immutable_trigger` trả lỗi khi cố ý `UPDATE`/`DELETE` |
| **Mạng nội bộ cách ly** | [`docker-compose.yml`](file:///C:/Users/Admin/Downloads/IPLMS/ai/docker-compose.yml) | Service `console` chỉ publish ra `127.0.0.1:8090`, không mở Traefik public route |

---

## 4. Kết luận nghiệm thu (Sign-off)

* **Kết luận:** Hệ thống AI Console nội bộ và các luồng gRPC/REST phụ trợ đáp ứng đầy đủ tiêu chuẩn bảo mật theo **IPLMS ADR-0048** và **ADR-0051**.
* **Đánh giá:** **PASS** — Đủ điều kiện an toàn thông tin để đưa vào bảo vệ đồ án tốt nghiệp.
* **Người phê duyệt:** Nguyễn Tấn Phát (`HiTranquility` — TechLead & M1 Owner).
