# 🔎 audit-1: Convention audit — bug-031 (gateway Traefik nhặt container của project khác)

> Mẫu của [convention audit](../../../../../../skills/iplms-code-review/references/convention-audit.md) (IPLMS ADR-0052). Auditor viết. Fixer chỉ sửa cột "Đã sửa" và đặt trạng thái `Fixed`. Auditor đặt `Verified`/`Reopened` và Kết luận.
> Hồ sơ: [bug-031](../bug.md).

| | |
|---|---|
| **Kết luận** | ✅ Không còn P0–P2 mở (2026-10-26, vòng 2): A-1 `Verified`. Còn 2 P3 Open (A-2, A-3), không chặn. |
| **Vòng** | 2/3 |
| **Phạm vi** | `ai/`, nhánh `bugfix/bug-031-2026-10-gateway-nhat-container-project-khac`, **phần đã stage** (`git -C ai diff --cached`): 6 file, +75/−1. Code/cấu hình: `docker-compose.yml`, `docker/traefik/traefik.yml`, `docker/traefik/traefik.develop.yml`, `docker/traefik/traefik.production.yml`. Tài liệu: `DESIGN.md`, `docs/projects/bugs/bug-031-gateway-nhat-container-project-khac/bug.md`. Không xét các file chưa stage (AGENTS.md, CLAUDE.md, ISSUE-002…011, SUGGESTION-006). |
| **Auditor** | Claude Code, subagent auditor độc lập, 2026-10-26. Không viết code chặng này. |
| **Fixer** | Claude Code (phiên điều phối) |
| **Máy quét** | `python -X utf8 script/audit/check_diff.py --staged --repo ai` (chạy từ gốc IPLMS): 4 file code, **0 FAIL, 0 WARN** (vòng 1 và vòng 2). |
| **Quy ước đã nạp** | `ai/DESIGN.md` §Traefik (`:21-41`, gồm luật "Console không label Traefik" ở `:11`) · `ai/docs/standards/AI_CONVENTIONS.md` (không có mục riêng về Traefik/compose) · IPLMS ADR-0055 "Đặt tên service, container, volume và mạng theo vai" Quyết định 4 (mạng `<project>_default` + mạng chung) · Traefik v3: docker provider `constraints` (`Label`, `LabelRegex`, `!`, `&&`, `\|\|`) và `loadbalancer.healthcheck.{path,port,scheme,mode,interval,timeout}` · `ai/docs/templates/bug-template.md` · CLAUDE.md "Surgical Changes" · convention-audit §3 |

## Kết quả chạy kiểm

| Lớp | Lệnh | Kết quả |
|---|---|---|
| Máy quét | `check_diff.py --staged --repo ai` | 0 FAIL, 0 WARN |
| Compose / unittest | `docker compose … config -q`, `test.test_docker_context`, `test.test_config` | Auditor **không chạy lại**. Kết quả OK lấy từ fixer. |
| Log gateway | `docker logs --since 10m -t iplms-ai-dev-gateway-1` (chỉ đọc) | Auditor tự chạy. Container khởi động lúc `11:51:15Z`. Mọi dòng `api@docker` / `compress@file` đều có giờ trước đó (dòng cuối ở `11:51:09Z`). Sau khi khởi động: **0 dòng**. |
| Prometheus | `traefik_service_server_up` qua `127.0.0.1:9090` (chỉ đọc) | Auditor tự chạy. Có 4 series bằng `1`: `ai-rest@docker` ×2 (`http://…:8000`), `ai-grpc@docker` ×2 (`h2c://…:50051`). Không còn service nào của eShop. |
| Vòng 2: nhãn đang chạy | `docker inspect iplms-ai-dev-api-{1,2}` (chỉ đọc) | Auditor tự chạy. Cả 2 replica mang `ai-grpc…healthcheck.mode=grpc`, không còn `healthcheck.port`, có `iplms.gateway=ai`. `api-1` khởi động `11:59:49Z`, `api-2` `12:01:42Z`. |
| Vòng 2: log gateway | `docker logs --since 12m iplms-ai-dev-gateway-1`, bỏ access log (chỉ đọc) | Auditor tự chạy. Cảnh báo health duy nhất là của `api@docker` (eShop, `172.21.0.3:8080`) lúc `11:50:36–11:51:06Z`, trước lần restart gateway `11:51:15Z`. Sau đó không có cảnh báo health nào; 4 phút cuối 0 dòng không phải access log. |
| Vòng 2: Prometheus | `traefik_service_server_up` (chỉ đọc), khoảng 50 s sau khi `api-2` lên | Auditor tự chạy. 4 series = `1`: `ai-grpc@docker` `h2c://172.24.0.5:50051` và `h2c://172.24.0.6:50051`, `ai-rest@docker` `http://172.24.0.5:8000` và `http://172.24.0.6:8000`. |
| Tắt replica / production / gRPC qua NestJS | — | NOT RUN bởi auditor (luật: không đổi container). Số 20/20 khi tắt `api-2` lấy từ fixer. Gap: chưa chạy compose production và chưa gọi gRPC từ backend sau thay đổi (bug.md đã ghi ở phần "Chưa kiểm"). |

### Ba điểm được giao kiểm

| Điểm | Kết luận | Bằng chứng |
|---|---|---|
| 1. Cú pháp `constraints: "Label(\`iplms.gateway\`, \`ai\`)"` | **Đúng Traefik v3.** Docker provider của v3 dùng biểu thức `Label(\`key\`, \`value\`)`. Biểu thức này so với mọi label của container, không chỉ label `traefik.*`. Cú pháp v2 (`constraints` dạng danh sách `tag==`) không còn dùng. | `traefik.yml:39`, `traefik.develop.yml:31`, `traefik.production.yml:39`. Runtime: router `api@docker` mất khỏi log, 4 server của AI vẫn lên (bảng trên). |
| 2. Service nào cần nhãn | **Chỉ `api` cần, và đã có** (`docker-compose.yml:42`). Trong base, develop, production và build compose, chỉ `api` có `traefik.enable=true`. `console` không có label Traefik (`docker-compose.yml:111`, DESIGN `:11`), nên không được thêm nhãn. `database-vector` không có label. `gateway` tự phục vụ ping/dashboard qua provider nội bộ (`api@internal`), không qua docker provider, nên constraint không ảnh hưởng. Healthcheck của develop (`docker-compose.develop.yml:46`) hỏi router `ai-rest@docker`, router này vẫn được nhận. | grep `traefik` trên `docker-compose*.yml` |
| 3. gRPC dò REST `:8000`, `scheme=http`, khi server scheme là `h2c` | **Hợp lệ về cú pháp và chạy được.** `healthcheck.scheme` thay scheme của URL server chỉ cho lượt dò, `healthcheck.port` thay cổng. Kết quả: lượt dò đi `http://<ip>:8000/health` thay vì `h2c://<ip>:50051`. Metric = 1 cho cả 2 server gRPC. **Nhưng lý do ghi trong code là sai:** AI có cài `grpc.health.v1.Health/Check` (xem A-1). | `docker-compose.yml:61-66`, `proto/health_service.proto:6`, `app/grpc_server.py:26` |

## Findings

| # | Mức | Loại | `file:line` | Luật bị vi phạm | Mô tả | Cách sửa đề xuất | Trạng thái | Đã sửa |
|---|---|---|---|---|---|---|---|---|
| A-1 | P2 | hợp-đồng | `docker-compose.yml:61`; `docs/projects/bugs/bug-031-gateway-nhat-container-project-khac/bug.md:40` | convention-audit §3.2 (đọc cả hai đầu hợp đồng, không suy từ tên); DESIGN "đổi kiến trúc phải cập nhật DESIGN cùng code" | Comment và bug.md ghi "health service gRPC của AI không phải `grpc.health.v1`", rồi dùng câu này làm lý do cho gRPC dò REST. Điều này sai. `proto/health_service.proto:6` khai `package grpc.health.v1;`. `app/grpc_server.py:26` đăng ký `add_HealthServicer_to_server`. `HealthHandler.Check` với `service=""` trả `SERVING` (`app/api/grpc/handlers/health_handler.py`). `app/script/grpc_smoke_check.py:160-164` cũng gọi đúng RPC này. Hệ quả: (a) người sau đọc comment sẽ tin không dùng được `mode=grpc`. (b) Dò REST chỉ biết uvicorn còn sống. Nếu tiến trình gRPC **treo** mà chưa thoát, Traefik vẫn chia tải vào replica đó. `docker-entrypoint.sh` (`wait -n`) chỉ bắt được trường hợp gRPC **thoát**. | Chọn một trong hai: **(A, khuyên dùng)** đổi `ai-grpc` sang `healthcheck.mode=grpc`, bỏ `port`/`scheme`. Server đã là `h2c`, Traefik gọi `Check` trên cleartext. Cần kiểm lại runtime: metric `traefik_service_server_up` của `ai-grpc` vẫn = 1, và trong Traefik v3.6 `path` có còn bắt buộc ở `mode=grpc` không. **(B)** Giữ cách dò REST nhưng sửa comment và bug.md theo lý do thật, ví dụ "dò REST để một nguồn sức khoẻ; gRPC chết thì entrypoint kéo container xuống". Ghi rõ không phát hiện được gRPC treo. Với cả hai cách, sửa cùng câu ở DESIGN `:28` nếu cách dò thay đổi. | Verified | Cách A: `docker-compose.yml` `ai-grpc` đổi sang `loadbalancer.healthcheck.mode=grpc`, bỏ `path`/`port`/`scheme` REST; comment theo lý do thật. `bug.md:40` và DESIGN §Traefik sửa câu. Runtime: không có cảnh báo health check, `server_up`=1 cho 2 server `ai-grpc`, tắt `api-2` thì `ai-grpc` chỉ còn `api-1` (Traefik v3.6 không đòi `path` ở `mode=grpc`). |
| A-2 | P3 | đúng-sai | `docker-compose.yml:42`; `docker/traefik/traefik*.yml` (constraint) | ADR-0055 QĐ4 (mỗi stack một mạng `<project>_default`) | Nhãn là hằng `ai`, không theo project. Nếu chạy hai stack AI trên cùng máy (ví dụ `iplms-ai-dev` và `iplms-ai-prod`, cổng host đổi qua `AI_GATEWAY_*_PORT`), mỗi gateway sẽ nhận `api` của cả hai stack. Hai stack cùng tên router/service `ai-rest`/`ai-grpc`, nên server của stack kia bị gộp vào cùng một service. Gateway không ở mạng `<project kia>_default`, nên không tới được các server đó. Health check mới sẽ đánh dấu chúng down, nên tác động thực tế nhỏ, nhưng log và metric sẽ nhiễu. Chưa có luật hay tình huống nào được ghi là phải hỗ trợ hai stack AI chạy song song. | Không chặn. Nếu cần: ràng theo nhãn Compose có sẵn, ví dụ `Label(\`com.docker.compose.project\`, \`…\`)`. Static file không nội suy biến, nên phải truyền constraint qua `command:` của `gateway` (`--providers.docker.constraints=…${COMPOSE_PROJECT_NAME}…`). Hoặc ghi một dòng ở DESIGN: "một stack AI mỗi Docker host". | Open | — |
| A-3 | P3 | quy-ước | `docker-compose.yml:50-54`, `:61-66`; `bug.md:40` | CLAUDE.md "Surgical Changes"; AGENTS.md (ý tưởng giữa chừng → SUGGESTION, một hồ sơ một nhánh) | Health check Traefik là "tối ưu gateway cùng lượt", không thuộc sửa lỗi bug-031 (lỗi là nhận nhầm container). Bug.md có ghi rõ điều này, nên không bị giấu. Thay đổi nhỏ, revert được, không đổi API. | Không chặn. Để lại trong nhánh thì giữ dòng "Cùng lượt" ở bug.md như hiện có. Nếu muốn đúng nguyên tắc một hồ sơ một việc thì tách phần healthcheck sang SUGGESTION/CHORE. | Open | — |

Trạng thái: `Open` → `Fixed` (fixer) → `Verified` (auditor) · `Reopened` · `Deferred` (P3, kèm hồ sơ theo dõi).
Loại: `quy-ước` · `hợp-đồng` · `đúng-sai` · `test` · `bảo-mật` · `hiệu-năng` · `tài-liệu`.

### Theo loại (Open + Reopened)

| Loại | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| đúng-sai | 0 | 0 | 0 | 1 (A-2) |
| quy-ước | 0 | 0 | 0 | 1 (A-3) |
| **Tổng** | **0** | **0** | **0** | **2** |

## WARN đã xét

Không có WARN.

## Bug đã mở

Không mở. A-1 là lý do sai và một khoảng trống phát hiện lỗi trong cấu hình mới, không phải hồi quy: trước bản sửa không có health check nào. A-2 chỉ xảy ra khi chạy hai stack AI cùng máy, chưa có luật nào yêu cầu hỗ trợ trường hợp này.

## Ngoài phạm vi (nợ cũ nhìn thấy)

- `docker-compose.yml:132` (service `console`, dòng ngữ cảnh, không đổi trong diff): `AI_CONSOLE_DATABASE_URL` có mật khẩu mặc định viết cứng trong `${AI_DB_PASSWORD:-…}`. Nên chuyển sang `${AI_DB_PASSWORD:?…}` hoặc chỉ để trong `.env`. Không tính vào kết luận.
- `docs/projects/issue-registry.md` ở repo gốc ghi mã bug kế tiếp của `ai` là `bug-030`, trong khi `bug-030` đã có (commit `e1a9646`). Bảng đã cũ, cần chạy lại `python -X utf8 script/issue_registry.py` (file này đang sửa dở ở gốc, không thuộc phạm vi).
- bug-031 chưa có trên `docs/projects/BOARD.md`. Đây không phải lỗi: BOARD sinh tự động trên `develop` (IPLMS ADR-0060), không sửa tay trong nhánh.

## Soát lại

Mỗi vòng (lượt auditor) một dòng. Tối đa 3 vòng. Vòng 2–3 chỉ soát delta của fixer và các finding `Fixed`: `git -C ai diff --cached <Tree> -- . ':!docs/projects/bugs/bug-031-gateway-nhat-container-project-khac/review/audit-1.md'`. `Tree` = `git write-tree` của index lúc bắt đầu vòng.

| Lần | Ngày | Tree | Finding đã soát | Kết quả |
|---|---|---|---|---|
| 1 | 2026-10-26 | `f394e78640e158cc5bc2a9a79f5ba1e9ce36d540` | Toàn bộ phần đã stage (6 file) | Mở A-1 (P2), A-2, A-3 (P3). Máy quét: 0 FAIL, 0 WARN. Log gateway sau restart: 0 dòng `api@docker`. `traefik_service_server_up` = 1 ×4 (auditor tự đọc). |
| 2 | 2026-10-26 | `b7daa85cc315f1964e99ed9680854cee3aa8e8a0` | A-1 (Fixed) và delta: `docker-compose.yml` (nhãn `ai-grpc`), `DESIGN.md` §Traefik, `bug.md` | A-1 → `Verified`. `ai-grpc` dùng `healthcheck.mode=grpc`, bỏ `path`/`port`/`scheme` REST; comment nêu đúng `grpc.health.v1`. Đầu kia hợp đồng: `proto/health_service.proto:6` (`package grpc.health.v1`), `app/grpc_server.py:26` (đăng ký servicer). DESIGN và `bug.md:40` khớp code. Delta không chạm gì khác. Runtime (auditor tự đọc): nhãn mới có trên 2 replica, log sau restart không có cảnh báo health, `server_up` = 1 ×4. Máy quét: 0 FAIL, 0 WARN. Không có finding mới. |
