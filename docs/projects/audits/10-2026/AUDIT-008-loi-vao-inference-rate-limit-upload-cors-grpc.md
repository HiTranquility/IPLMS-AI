# 🚪 AUDIT-008: Lối vào inference của AI (gateway, rate-limit, upload ảnh ANPR, CORS, gRPC) vs AI_CONVENTIONS và các rào chắn bug-032

> **Đích:** `docs/projects/audits/10-2026/AUDIT-008-loi-vao-inference-rate-limit-upload-cors-grpc.md` · **Luật chung:** [templates/README](../../../templates/README.md)

## 📌 Meta

| | |
|---|---|
| **ID** | AUDIT-008 |
| **Trạng thái** | 🛠️ Đang khắc phục: cả 5 lỗ hổng nhóm A đã sửa trên nhánh bugfix riêng (2026-10-27), chờ PR merge rồi chạy lại §5. Nhóm B và OPEN-01 còn mở |
| **Ngày quét** | 2026-10-27 |
| **Người quét** | Claude Code, một lượt, theo câu hỏi của @HiTranquility (không có auditor độc lập, không có vòng 2) |
| **Phạm vi (Scope)** | Process inference của `ai/` trên `develop` `f25b747`: `app/main.py`, `app/api/rest/**` (trừ `console_*`), `app/grpc_server.py`, `app/core/vision/services/anpr_service.py`, `docker-compose*.yml`, `docker/traefik/**`. Thêm đường vào từ ngoài: `backend/src/modules/Parking/controllers/staff/checkin-checkout-operation.controller.ts` và Helm `deployment/helm/iplms` (phần `ai`) |
| **Không thuộc phạm vi** | AI Console (đã soát ở [AUDIT-005](AUDIT-005-ai-console-security-review.md), [AUDIT-006](AUDIT-006-console-wip-2026-10-25.md), [AUDIT-007](AUDIT-007-develop-2026-10-27-console-knowledge-settings.md)); app mobile; chất lượng model ANPR |
| **Quy ước đối chiếu** | [AI_CONVENTIONS](../../../standards/AI_CONVENTIONS.md); ghi chú `bug-032` ở `docker-compose.yml:150` và Helm `templates/networkpolicy-ai.yaml` (AI không có xác thực, chỉ được gọi từ backend); OWASP ASVS v4.0.3 V12.1 (giới hạn file upload) và V14.5 (CORS) |
| **Người/agent sẽ sửa** | @HiTranquility (Claude Code thực hiện): `bugfix/bug-043…046-2026-10-*` ở ai, `bugfix/bug-019-2026-10-anpr-upload-limits` ở backend |
| **Tags** | `security`, `rate-limit`, `upload`, `cors`, `grpc`, `gateway`, `dos` |

---

## 1. Luật gốc đang đo

> **Rào chắn bug-032:** "chỉ bind localhost — AI không có xác thực; backend gọi qua alias ai-gateway trên mạng chung." *Nguồn: `docker-compose.yml:150`*. Helm: "AI service không có lớp xác thực riêng — chỉ pod api/worker của release này được gọi vào". *Nguồn: `deployment/helm/iplms/templates/networkpolicy-ai.yaml:2-3`*

Vì AI cố ý không có xác thực, mọi rào chắn còn lại phải nằm ở **lớp mạng** và ở **giới hạn tài nguyên trong chính process**: kích thước, số lượng, đồng thời, origin. Audit này đo các giới hạn đó.

> **OWASP ASVS V12.1.1:** ứng dụng không nhận file lớn có thể làm đầy bộ nhớ hoặc ổ đĩa và gây từ chối dịch vụ.

> **OWASP ASVS V14.5.3:** header CORS `Access-Control-Allow-Origin` dùng danh sách cho phép nghiêm ngặt các domain tin cậy, không dùng "null".

**Chuẩn vàng:** ANPR thử trong Console, `app/api/rest/routes/console_tools_controller.py:188`: `await file.read(KNOWLEDGE_MAX_FILE_BYTES + 1)` rồi từ chối nếu vượt 8 MB. Chỉ đọc tối đa N+1 byte nên file lớn không vào được RAM.

## 2. Phương pháp quét

```bash
# Chạy trong ai/ (trừ dòng có ghi backend/ hoặc deployment/, chạy từ gốc IPLMS)
grep -rniE "rate.?limit|slowapi|throttl|limiter|max_file|content.?length" --include=*.py app
grep -niE "ratelimit|inflightreq|middlewares" docker/traefik/*.yml docker-compose*.yml
grep -n "file.read()" app/core/vision/services/anpr_service.py
grep -nE "allow_origins|allow_credentials" app/api/rest/middlewares/cors.py
grep -nE "add_insecure_port|maximum_concurrent_rpcs|max_workers|interceptors=" app/grpc_server.py
grep -rnE "RateLimitGuard|ThrottlerModule" backend/src --include=*.ts      # từ gốc IPLMS
grep -nE "FileInterceptor|fileSize|fileFilter" backend/src/modules/Parking/controllers/staff/checkin-checkout-operation.controller.ts
grep -nE "replicaCount|networkPolicy" deployment/helm/iplms/values*.yaml
```

Tái hiện trong process bằng `TestClient` của FastAPI. Hai script nằm trong scratchpad của phiên, không đưa vào repo. Inference thật được thay bằng stub, nên không cần model:

| Ca | Kết quả |
|---|---|
| `POST /api/anpr/recognize`, file `x.txt` 60 MB, `text/plain` | `200`, stub nhận **62 914 560 byte**: cả file đã vào RAM, không kiểm MIME. Message trả về chứa nguyên chuỗi exception của stub (`Recognition failed: stub: /secret/path/model.pt not found`) |
| `POST /api/anpr/recognize-many`, 500 file | `200`, **500/500 file** được đưa vào nhận diện trong cùng một request |
| `OPTIONS` và `GET` với `Origin: https://evil.example` qua `register_cors` | `access-control-allow-origin: https://evil.example`, `access-control-allow-credentials: true` |

- **Đã quét:** 6 controller REST inference, `grpc_server.py`, 3 file Traefik, 3 file compose, 1 controller backend, 3 file values Helm.
- **Tổng phát hiện:** 🟠 5 phải sửa (đã mở bug) · 🟡 5 cần xem · ⚪ 7 hợp lệ.

**Vì sao không có 🔴:** process inference không được đưa ra Internet. Compose chỉ bind `127.0.0.1` (`docker-compose.yml:152-154`), còn Helm ingress không định tuyến tới AI (`deployment/helm/iplms/templates/ingress.yaml:26-27`). Kẻ tấn công cần đứng trong mạng nội bộ, hoặc dùng trình duyệt của developer (xem A3). Riêng A5 ở backend thì công khai, nhưng phải có tài khoản staff.

## 3. Phát hiện

### 🟠 Nhóm A — Lỗ hổng, phải sửa

| # | `file:line` | Hiện trạng | Vì sao sai | Cách xử lý (→ đích) |
|---|---|---|---|---|
| A1 | `app/core/vision/services/anpr_service.py:18`; `app/api/rest/routes/anpr_controller.py:17-24` | `image_bytes = await file.read()` đọc hết file, không giới hạn byte, không kiểm `content_type`/magic byte, rồi đưa vào `cv2.imdecode` | ASVS V12.1.1. Lệch chuẩn vàng 8 MB của Console. Một request vài trăm MB là đủ đẩy pod (limit 2 GB ở `docker-compose.production.yml`) vào OOM | Đọc tối đa `ANPR_MAX_BYTES + 1` (dùng chung hằng 8 MB), chỉ nhận `image/jpeg`/`image/png` và kiểm magic byte, trả 413/415. → [bug-043](../../bugs/bug-043-anpr-rest-doc-anh-khong-gioi-han-kich-thuoc/bug.md) |
| A2 | `app/api/rest/routes/anpr_controller.py:28-46` | `recognize-many` nhận `List[UploadFile]`. Giới hạn duy nhất là mặc định `max_files=1000` của Starlette 1.6.0. Mỗi file chạy YOLO+OCR tuần tự trong cùng request | Một request chiếm CPU vài phút (ước tính 500 file × thời gian ANPR một ảnh), chặn tài nguyên của đường nóng gRPC dùng chung process | Đặt trần số file (ví dụ 10) và tổng byte, trả 413 khi vượt. Cân nhắc bỏ endpoint nếu không còn ai gọi. → [bug-044](../../bugs/bug-044-anpr-recognize-many-khong-gioi-han-so-file/bug.md) |
| A3 | `app/api/rest/middlewares/cors.py:14-15`; gắn ở `app/main.py:39` | `allow_origins=["*"]` cùng `allow_credentials=True`. Starlette phản chiếu nguyên origin của request và trả `allow-credentials: true`. Docstring ở `cors.py:9-10` đã ghi production phải thu hẹp, nhưng `docker-compose.production.yml` không đổi | ASVS V14.5.3. AI không có xác thực, nên **bất kỳ trang web nào** developer mở đều đọc được phản hồi của `127.0.0.1:8000`: Copilot, forecast, ANPR. Trang đó cũng đốt được CPU/LLM của máy dev. Đây là đường vòng qua rào "chỉ bind localhost" | Lấy danh sách origin từ config (rỗng ở production vì chỉ backend gọi server-to-server), bỏ `allow_credentials`. → [bug-045](../../bugs/bug-045-cors-inference-phan-chieu-moi-origin-kem-credentials/bug.md) |
| A4 | `docker/traefik/traefik.yml:23-31`, `traefik.production.yml:23-31` (không có middleware); `app/grpc_server.py:37-44` (không có `maximum_concurrent_rpcs`); `app/config/server_config.py:14` (`grpc_max_workers=10`) | Traefik cân bằng tải và dò health nhưng không có `rateLimit` hay `inFlightReq`. gRPC server không giới hạn số RPC đồng thời, nên request dư xếp hàng không trần. Helm không dùng Traefik, nên ở K3s không có lớp nào giới hạn | Mọi rào tài nguyên đang dựa vào việc backend gọi có chừng mực. Các route staff ANPR của backend không có `RateLimitGuard` (B4). Burst làm hàng đợi phình, check-in timeout hàng loạt | Đặt `maximum_concurrent_rpcs` ở `aio.server` và trả `RESOURCE_EXHAUSTED` khi đầy (chạy được cả compose lẫn Helm). Thêm middleware `inFlightReq` + `rateLimit` cho router REST trong Traefik. → [bug-046](../../bugs/bug-046-loi-vao-ai-khong-gioi-han-toc-do-va-dong-thoi/bug.md) |
| A5 | `backend/src/modules/Parking/controllers/staff/checkin-checkout-operation.controller.ts:69, :83, :108` | `FileInterceptor('file')` không có `limits.fileSize` hay `fileFilter`. Multer không đặt `dest` nên dùng memory storage: cả file nằm trong RAM của pod backend trước khi tới AI. AI lại chặn ở 10 MB (`grpc_max_message_length`), nên file lớn hơn vừa tốn RAM vừa hỏng | Lỗ công khai duy nhất của nhóm này (staff đã đăng nhập). Một tài khoản staff bị lộ, hoặc client lỗi, là đủ làm OOM pod API | Thêm `limits: { fileSize: 8 MB, files: 1 }` và `fileFilter` theo MIME ảnh cho 3 route. → [backend bug-019](../../../../../backend/docs/projects/bugs/bug-019-upload-anpr-staff-khong-gioi-han-kich-thuoc/bug.md) |

### 🟡 Nhóm B — Cần xem lại / lệch nhẹ

| # | `file:line` | Hiện trạng | Đề xuất |
|---|---|---|---|
| B1 | `app/api/rest/routes/anpr_controller.py:24` | Lỗi trả `f"Recognition failed: {exc}"` cho client, có thể lộ đường dẫn file và tên model | Trả mã lỗi chung, log chi tiết kèm `request_id`. Sửa cùng bug-043 |
| B2 | `app/grpc_server.py:71` | `add_insecure_port`: không TLS, interceptor chỉ có logging (`app/api/grpc/interceptors/logging_interceptor.py:61`), không token nội bộ | Chấp nhận được khi lớp mạng giữ chặt. Nếu mạng không giữ được (B3) thì cần token dùng chung qua metadata hoặc mTLS. Người quyết: OPEN-01 |
| B3 | `deployment/helm/iplms/values.yaml:67-68`; `values-prod.yaml` không ghi đè | NetworkPolicy của AI **mặc định tắt và chưa bật ở prod**. Comment ghi là chờ kiểm probe kubelet trên cụm thật. Khi tắt, mọi pod trong cụm gọi được AI REST/gRPC mà không cần xác thực | Thuộc repo `deployment`: kiểm probe rồi bật `ai.networkPolicy.enabled: true` ở `values-prod.yaml`. Gắn với quyết định nơi deploy K3s đang chờ |
| B4 | `backend/.../checkin-checkout-operation.controller.ts:41-43` | Route staff ANPR chỉ có `AuthGuard` + `RolesGuard`, không có `RateLimitGuard` (guard có sẵn ở `backend/src/utils/pipelines/guards/rate-limit.guard.ts` và đã dùng cho auth, Copilot, thanh toán, đặt chỗ) | Gắn `@RateLimit` theo `user` cho 3 route upload. Chi phí thấp nhất trong các cách chặn burst của A4 |
| B5 | `deployment/helm/iplms/values-prod.yaml:57-60`; compose chỉ có một service `api` | AI ở prod chạy **1 replica** (mỗi bản tốn ~1.4 GiB, khởi động ~20 s). Cân bằng tải và healthcheck của Traefik có cấu hình nhưng chưa chia tải thật; replica chết là ANPR ngừng | Ghi rõ là single-point-of-failure có chủ đích trong DESIGN. Khi có node đủ RAM thì lên 2 replica + PodDisruptionBudget |

### ⚪ Nhóm C — Hợp lệ (đã đúng, không sửa)

| `file:line` | Chỗ | Vì sao đạt |
|---|---|---|
| `docker-compose.yml:152-154` | Gateway chỉ bind `127.0.0.1` | Đúng rào bug-032 cho máy dev |
| `deployment/helm/iplms/templates/ingress.yaml:26-27` | Không có ingress tới AI | AI không ra Internet |
| `docker-compose.yml:49-65` | Traefik dò `/health` và gRPC health mỗi 5 s | Loại replica hỏng, có metric `traefik_service_server_up` |
| `app/grpc_server.py:43-44`; `app/config/server_config.py:16` | `max_receive/send_message_length` = 10 MB | Chặn message gRPC lớn ở đường nóng check-in |
| `app/api/rest/routes/vision_controller.py:16`; `app/api/rest/developer_access.py:35-43` | `/vision/*` cần loopback trực tiếp + same-origin, tối đa 20 lần/phút | Endpoint chẩn đoán có rào, mặc định tắt (`server_config.py:22`) |
| `app/infra/storage/object_store.py:52, :69-75` | Tải ảnh qua URL: chỉ https, có timeout, cắt theo `max_bytes` | Hạn chế SSRF qua http thường và tải file quá lớn |
| `backend/src/utils/pipelines/guards/rate-limit.guard.ts` | `RateLimitGuard` dựa trên cache, đếm theo IP/user, đã gắn ở auth, Copilot, thanh toán, đặt chỗ, slot hold | Backend **có** rate-limit cho các route công khai chính. Phần thiếu chỉ là route staff ANPR (B4) |

### ❓ Chờ người quyết

| Mã | Câu hỏi | Phương án |
|---|---|---|
| OPEN-01 | Có thêm xác thực cho gRPC backend→AI không, hay giữ "tin lớp mạng"? | (a) Giữ nguyên, bắt buộc bật B3 trước production. (b) Token dùng chung qua metadata + interceptor: rẻ, xoay vòng tay. (c) mTLS: chắc nhất, tốn công cấp cert. Khuyến nghị (a) ngay, rồi (b) khi có nhiều hơn một cụm hoặc tenant |

## 4. Việc giao cho người/agent sửa

1. **bug-043 + B1:** `anpr_service.py` / `anpr_controller.py`: đọc giới hạn byte, kiểm MIME và magic byte, trả lỗi chung. Thêm test ở `test/` cho các ca 60 MB → 413, `text/plain` → 415, ảnh hợp lệ → 200.
2. **bug-044:** trần số file và tổng byte cho `recognize-many`, kèm test 11 file → 413.
3. **bug-045:** origin lấy từ config (`app/config/server_config.py`), bỏ credentials. Test: preflight với origin lạ không trả `access-control-allow-origin`.
4. **bug-046:** `maximum_concurrent_rpcs` (cấu hình được) ở `grpc_server.py`; middleware Traefik ở cả `traefik.yml` lẫn `traefik.production.yml`, gắn qua label router `ai-rest`.
5. **backend bug-019 + B4:** 3 route upload staff: `limits.fileSize`, `fileFilter`, `@RateLimit`.
6. **B3:** mở việc ở repo `deployment` khi chốt nơi deploy.
7. **Verify:** `python -m unittest discover -s test` xanh trong `ai/`; `npx tsc --noEmit` và jest của module Parking xanh trong `backend/`; chạy lại các lệnh ở §2 và §5.
8. **Commit** từng bug một nhánh `bugfix/bug-NNN-2026-10-<slug>` (**[NEVER]** `git add .`).

## 5. Kiểm tra tuân thủ lại

```bash
grep -c "file.read()" app/core/vision/services/anpr_service.py                       # kỳ vọng 0
grep -cE 'allow_origins=\["\*"\]' app/api/rest/middlewares/cors.py                    # kỳ vọng 0
grep -c "maximum_concurrent_rpcs" app/grpc_server.py                                  # kỳ vọng ≥ 1
grep -ciE "inflightreq|ratelimit" docker-compose.yml docker/traefik/*.yml             # kỳ vọng ≥ 1
grep -c "fileSize" ../backend/src/modules/Parking/controllers/staff/checkin-checkout-operation.controller.ts  # kỳ vọng 3
```

Chạy lại hai ca tái hiện ở §2: 60 MB → 413, 500 file → 413, origin lạ → không có header CORS.

- **Lúc quét:** 5 lỗ hổng 🟠 · **Kỳ vọng sau sửa:** 0 (Nhóm B xử lý theo quyết định riêng).

## 6. Liên kết

- Sinh ra từ: câu hỏi của @HiTranquility trong chat ngày 2026-10-27 ("IPLMS-AI có chặn rate-limiting, gateway, phân tải, bảo mật test hình ảnh… audit thế nào chưa?").
- Đẻ ra: [bug-043](../../bugs/bug-043-anpr-rest-doc-anh-khong-gioi-han-kich-thuoc/bug.md) · [bug-044](../../bugs/bug-044-anpr-recognize-many-khong-gioi-han-so-file/bug.md) · [bug-045](../../bugs/bug-045-cors-inference-phan-chieu-moi-origin-kem-credentials/bug.md) · [bug-046](../../bugs/bug-046-loi-vao-ai-khong-gioi-han-toc-do-va-dong-thoi/bug.md) · [backend bug-019](../../../../../backend/docs/projects/bugs/bug-019-upload-anpr-staff-khong-gioi-han-kich-thuoc/bug.md)
- Liên quan: [AUDIT-005](AUDIT-005-ai-console-security-review.md) (Console, đã đóng) · [bug-037](../../bugs/bug-037-copilot-gateway-khong-gioi-han-prompt-va-guard-bi-lach-chu/bug.md) (giới hạn prompt ở gateway Copilot)
