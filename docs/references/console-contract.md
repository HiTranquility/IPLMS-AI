# Hợp đồng AI Console (M0)

> Mô tả **đúng code hiện có** (IPLMS ISSUE-126 phase-6 mục 6.7), không thiết kế mới. Code là nguồn chuẩn: lệch thì sửa file này theo code. Quyết định gốc: IPLMS ADR-0048, ADR-0049, ADR-0050, ADR-0051.

## 1. Quy ước chung

| Mục | Giá trị | Nguồn |
|---|---|---|
| Gốc API | `/api` trên process `app.console_main` (`127.0.0.1:8090`) | `app/console_main.py` |
| Envelope thành công | `{ success: true, total, message, data: [] }` — `data` luôn là mảng | `app/api/rest/schemas/base_response.py` |
| Envelope lỗi | `{ success: false, total: 0, message, data: [], code }` | `app/console_main.py` `_error` |
| Phiên | Cookie httpOnly, `SameSite=Strict`, `Secure` theo `AI_CONSOLE_COOKIE_SECURE`; DB giữ SHA-256 của token | `app/api/rest/console_access.py`, `auth_service.py` |
| Chống CSRF | Mọi request ghi (không phải GET/HEAD/OPTIONS) phải có header `X-Console-Request: 1`; `Sec-Fetch-Site: cross-site` bị chặn | `require_same_origin_write` |
| Thời hạn | Phiên ≤ 8 giờ, rảnh 30 phút; step-up ≤ 5 phút | `app/config/console_config.py` |
| Thử sai | 5 lần sai TOTP trong một phiên → huỷ phiên; 5 lần sai mật khẩu khẩn cấp → khoá 15 phút | `auth_service.py` `MAX_AUTH_FAILURES` |

### Mã lỗi

| HTTP | `code` | Khi nào |
|---|---|---|
| 400 | `INVALID_INPUT` | Validate thất bại (`ValueError`) |
| 401 | `UNAUTHENTICATED`, `SESSION_EXPIRED`, `SESSION_IDLE`, `SESSION_REVOKED`, `MEMBER_DISABLED` | Không có/hết phiên |
| 401 | `MFA_REQUIRED` | Có phiên nhưng chưa qua TOTP |
| 401 | `STEP_UP_REQUIRED` | Quyền nhạy cảm, cần `POST /auth/step-up` trước |
| 401 | `NOT_INVITED`, `NOT_CONFIGURED`, `TOTP_INVALID`, `TOTP_NOT_ENROLLED`, `TOTP_ALREADY_ENROLLED`, `TOO_MANY_ATTEMPTS` | Bước đăng nhập |
| 403 | `FORBIDDEN` | Thiếu quyền, vi phạm bốn mắt, thiếu header CSRF |

Callback Google không trả JSON: chuyển về `/?login_error=<code>` (thêm `GOOGLE_DENIED` khi người dùng huỷ ở Google).

## 2. Vai trò và quyền

Một nguồn: `app/core/console/engines/access_policy.py`. Admin/Moderator của platform **không** tự có vai trò nào.

| Quyền | analyst | annotator | reviewer | data_eng | ml_eng | lead | console_admin |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| `ai:metrics:read` | ✓ | | ✓ | ✓ | ✓ | ✓ | |
| `ai:task:label` | | ✓ | ✓ | | | | |
| `ai:label:approve` | | | ✓ | | | ✓ | |
| `ai:chatlog:read` | ✓ | | ✓ | | ✓ | ✓ | |
| `ai:pii:reveal` 🔐 | | | | ✓ | | ✓ | |
| `ai:pipeline:manage` | | | | ✓ | | ✓ | |
| `ai:dataset:snapshot` | | | | ✓ | ✓ | ✓ | |
| `ai:golden:freeze` 🔐 | | | | | | ✓ | |
| `ai:model:evaluate` | | | | | ✓ | ✓ | |
| `ai:model:propose` | | | | | ✓ | ✓ | |
| `ai:model:promote` 🔐 | | | | | | ✓ | |
| `ai:prompt:edit` | | | | | ✓ | ✓ | |
| `ai:policy:threshold` 🔐 | | | | | | ✓ | |
| `ai:member:manage` | | | | | | | ✓ |
| `ai:audit:read` | | | | | | ✓ | ✓ |

🔐 = cần step-up (`STEP_UP_PERMISSIONS`). Vai trò đầy đủ có tiền tố `ai_` (`ai_lead`, `ai_console_admin`…).

## 3. Endpoint

Mọi đường dẫn dưới đây nằm sau `/api`.

### Đăng nhập — `console_auth_controller.py`

| Method | Đường dẫn | Quyền | Body → `data[0]` |
|---|---|---|---|
| GET | `/auth/google/start` | — | 302 sang Google (PKCE + nonce), đặt cookie flow |
| GET | `/auth/google/callback` | — | 302 về `/`, đặt cookie phiên |
| POST | `/auth/password` | — | `{email, password}` → `{mfa_required: true}` |
| POST | `/auth/totp/enroll` | phiên | → `{otpauth_uri}` |
| POST | `/auth/totp` | phiên | `{code}` → `{mfa_required: false}` |
| POST | `/auth/step-up` | phiên + MFA | `{code, reason}` |
| POST | `/auth/logout` | phiên | — |
| GET | `/me` | phiên | `{member_id, email, display_name, roles[], permissions[], mfa_done, totp_enabled, totp_pending}` — `permissions` rỗng khi chưa qua MFA |

### Thành viên & audit — `console_member_controller.py`

| Method | Đường dẫn | Quyền |
|---|---|---|
| GET | `/members` | `ai:member:manage` |
| POST | `/members` | `ai:member:manage` — mời theo email |
| POST | `/members/{member_id}/roles/{role}` | `ai:member:manage` — cấp, cần lý do; không tự cấp cho mình |
| POST | `/members/{member_id}/roles/{role}/revoke` | `ai:member:manage` |
| GET | `/audit` | `ai:audit:read` — `audit_event` chỉ-thêm (trigger chặn UPDATE/DELETE/TRUNCATE) |

### Copilot Lab — `console_copilot_controller.py` (tiền tố `/copilot`)

| Method | Đường dẫn | Quyền |
|---|---|---|
| GET | `/copilot/usage` | `ai:metrics:read` — tóm tắt mức dùng từ `ai_request_log` (ADR-0049) |
| GET | `/copilot/review-stats` | `ai:metrics:read` — tỉ lệ đúng trên lượt đã chấm |
| GET | `/copilot/turns` | `ai:chatlog:read` — lượt gần nhất, chỉ cột đã che PII, không trả `user_hash` |
| POST | `/copilot/turns/{turn_id}/review` | `ai:label:approve` — `CORRECT` / `INCORRECT` / `UNSAFE` |

### Công cụ thử — `console_tools_controller.py` (tiền tố `/tools`, ADR-0050)

| Method | Đường dẫn | Quyền |
|---|---|---|
| GET | `/tools/system` | `ai:metrics:read` — cấu hình chỉ "đã/chưa", không lộ giá trị |
| POST | `/tools/copilot` | `ai:prompt:edit` — hỏi thử, ghi `ai_request_log` với `task = console_try` |
| POST | `/tools/knowledge` | `ai:prompt:edit` — multipart, chỉ tạo bản nháp; ghi `audit_event` |

### Vision — `console_vision_controller.py` (tiền tố `/vision`)

| Method | Đường dẫn | Quyền |
|---|---|---|
| GET | `/vision/status` | `ai:metrics:read` — số mẫu A2, lỗi nhận gần nhất |
| GET | `/vision/queue` | `ai:task:label` |
| GET | `/vision/samples/{capture_id}/crop` | `ai:task:label` hoặc `ai:label:approve` — trả ảnh |
| POST | `/vision/samples/{capture_id}/labels` | `ai:task:label` |
| GET | `/vision/reviews` | `ai:label:approve` |
| POST | `/vision/labels/{label_id}/decision` | `ai:label:approve` — bốn mắt: không duyệt nhãn của mình |
| GET | `/vision/snapshots` | `ai:dataset:snapshot` hoặc `ai:model:evaluate` |
| POST | `/vision/snapshots` | `ai:dataset:snapshot` |
| POST | `/vision/snapshots/{snapshot_id}/freeze` | `ai:golden:freeze` 🔐 |
| GET | `/vision/models` | `ai:metrics:read` |
| POST | `/vision/models` | `ai:model:propose` |
| POST | `/vision/models/{model_id}/propose` | `ai:model:propose` |
| POST | `/vision/models/{model_id}/promote` | `ai:model:promote` 🔐 — bốn mắt |
| GET | `/vision/evals` | `ai:metrics:read` |
| POST | `/vision/evals` | `ai:model:evaluate` |
| GET | `/vision/accuracy` | `ai:metrics:read` — chỉ trên mẫu bốc ngẫu nhiên có nhãn người |
| GET | `/vision/policies` | `ai:metrics:read` |
| POST | `/vision/policies` | `ai:model:propose` — ngưỡng 0.50–0.99, bốc kiểm 1–50% |
| POST | `/vision/policies/{policy_id}/decision` | `ai:policy:threshold` 🔐 — bốn mắt |

## 4. gRPC (process inference, cổng 50051)

| RPC | Chiều | Ghi chú |
|---|---|---|
| `DatasetService.ExportForConsole` | backend → AI | Kênh A2: lô rỗng = hỏi watermark; ≤ 200 mẫu/lượt; không có `sessionId`/user/`areaId` rõ (ADR-0048 §5) |
| `DatasetService.GetAcceptPolicy` | backend kéo | Bản `accept_policy` APPROVED gần nhất; `found = false` khi chưa có (ADR-0051) |
| `CopilotService.GetUsageSummary` | backend → AI | Thẻ mức dùng ở platform (ADR-0049) |
| `CopilotService.RecordFeedback` | backend → AI | 👍/👎 của chủ lượt |

Proto ở `proto/` phải giống từng byte với `backend/src/infrastructures/Ai/proto/` và `proto/` của repo gốc.

## 5. Event stream chat (Copilot)

`AskStream` (proto `copilot_service.proto`): các chunk văn bản, chunk cuối có `is_finished = true` kèm `turn_id` và `prompt_version`. Hai trường này chỉ cộng thêm — client cũ bỏ qua được. `turn_id` dùng cho `RecordFeedback`.

## 6. Token giao diện

`ai/ui/src/index.css` dùng **cùng tên token** với ba app frontend (`--color-bg`, `--color-surface`, `--color-accent`, `--color-accent-ink`, `--space-*`, `--text-*`, `--radius-*`…), giá trị riêng, có light/dark. Luật đầy đủ: [ui/DESIGN.md](../../ui/DESIGN.md).
