# 📐 ADR-0006: Build context của image AI là chính repo IPLMS-AI, proto lấy từ bản chép `proto/`

> **Đích:** `docs/projects/adrs/10-2026/0006-build-context-la-repo-ai.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Accepted |
| **Ngày** | 2026-10-31 |
| **Người quyết định** | HiTranquility (chốt trong chat 2026-10-31: phương án A) |
| **Phạm vi** | Đặt ở repo AI vì đây là quyết định đóng gói image của AI; hợp đồng proto (nguồn chuẩn, `check_proto_sync.py`) không đổi. Nếu cần ADR ở IPLMS gốc thì ADR này trỏ sang. IPLMS-AI: `Dockerfile`, `.dockerignore`, `docker-compose*.yml`, `.github/workflows/image.yml`, `proto/`. Thay phần "context phải là gốc repo" của IPLMS PROB-034 và [AI_CONVENTIONS §7](../../../standards/AI_CONVENTIONS.md#7-build-image--context-là-chính-repo-ai) bản cũ |

## Bối cảnh

`Dockerfile` cũ dùng context là **gốc repo cha IPLMS** (`COPY ai/...` + `COPY proto`), vì hợp đồng gRPC nguồn chuẩn nằm ở `IPLMS/proto/`. IPLMS PROB-034 (09-2026) đã cân nhắc build từ `ai/` (phương án B) rồi bỏ, với lý do "phải chép `proto/` vào trước mỗi lần build, dễ quên ⇒ stub cũ".

[bug-003](../../bugs/bug-003-docker-context-khong-dong-bo/bug.md) (2026-10-15, P1) cũng đã chặn một lần đổi y hệt, vì đổi COPY mà không sửa CI, caller và allowlist cùng đợt. Điều kiện để làm lại: "thiết kế riêng rồi cập nhật CI/caller và allowlist cùng đợt". ADR này đáp ứng điều kiện đó ở mục Hệ quả › Caller.

Từ đó tình hình đã khác:

- Repo này đã có `proto/` chép sẵn và được version (ISSUE-006, cho CI đứng riêng). `IPLMS/proto/check_proto_sync.py` canh nó không lệch với nguồn chuẩn.
- `image.yml` phải checkout repo vào `./ai` rồi `cp -r ai/proto proto` để dựng lại bố cục umbrella. Tức là CI vẫn phải chép đúng như PROB-034 lo ngại, chỉ là chép ẩn trong workflow.
- Đề Final Project §9 yêu cầu README có cách chạy. Người chấm clone repo IPLMS-AI (public) về thì `docker compose up` hỏng ngay, vì `context: ..` trỏ ra ngoài repo.

## Quyết định

1. Build context là **chính repo IPLMS-AI**: `docker build -t iplms-ai:latest .`. `Dockerfile` chỉ COPY đường dẫn trong repo, kể cả `proto/`. Compose dùng `context: .`. Caller ngoài repo phải trỏ context vào thư mục `ai/`, không phải gốc umbrella (xem Hệ quả › Caller).
2. Allowlist build gộp về **một** file `.dockerignore` ở gốc context, áp cho cả BuildKit lẫn builder cũ. Bỏ `Dockerfile.dockerignore`.
3. `IPLMS/proto/` vẫn là nguồn chuẩn. Đổi hợp đồng thì sửa ở đó, chép sang `proto/` của repo này **cùng đợt**, và `check_proto_sync.py` phải xanh. Không sửa tay `proto/` ở đây.

## Các phương án đã cân nhắc

| Phương án | Vì sao không chọn |
|---|---|
| B. Giữ context umbrella, chỉ ghi rõ README | Clone riêng vẫn không build được; CI vẫn phải dựng lại bố cục bằng `cp` |
| C. Chuyển nguồn chuẩn proto sang IPLMS-AI | Đụng backend (NestJS nạp proto riêng) và CI repo cha; quá lớn so với nhu cầu |

## Hệ quả

### Được

- Clone riêng là build được; README chạy đúng như viết.
- `image.yml` bớt bước dựng bố cục giả; image build từ đúng thứ có trong repo.

### Đánh đổi

- Có hai bản proto; chống lệch dựa vào `check_proto_sync.py` ở CI repo cha. Đổi proto mà quên chép thì image AI dùng hợp đồng cũ.
- Caller nào còn gọi `docker build -f ai/Dockerfile .` từ gốc umbrella sẽ hỏng ở `COPY requirements-service.txt`, vì COPY không còn tiền tố `ai/`.

### Caller (rà 2026-10-31)

| Caller | Trạng thái |
|---|---|
| `deployment/script/run-stack.{ps1,sh}` | Gọi `ai/docker-compose.yml`; compose tính `context: .` theo thư mục file, không phải sửa |
| `deployment/registry/push-images-local.{ps1,sh}:18` | Build context gốc. Sửa sang context `ai/` trên nhánh cùng tên ở IPLMS-Deployment |
| `deployment/docs/guides/09-2026/operations.md:267` | Hướng dẫn cũ "context phải là gốc repo". Sửa cùng nhánh Deployment |
| `backend/docker-compose.yml:247–248` (theo bug-003; service AI `context: ..` + `dockerfile: ai/Dockerfile`) | **Chưa rà được**: phiên làm việc không có quyền đọc IPLMS-Backend. **Chặn:** không nâng gitlink `ai` ở umbrella tới khi caller này đổi sang `context: ../ai`, `dockerfile: Dockerfile` (theo dõi ở bug-053 › Việc trên BOARD) |
| IPLMS `/.dockerignore` (allowlist cho context umbrella) | Hết tác dụng với image AI khi mọi caller đã đổi; dọn ở IPLMS gốc sau khi gỡ chặn ở trên |

## Bằng chứng và liên kết

- [bug-053](../../bugs/bug-053-db-init-hong-va-build-can-repo-cha/bug.md): build probe từ bản `git archive` của nhánh, không có repo cha: sinh đủ 7 stub, có `data/prompts/`, không lọt `.env*`.
- `test/test_docker_context.py` (`AI_RUN_CONTEXT_FIXTURE=1`) xanh với allowlist mới.
- [bug-003](../../bugs/bug-003-docker-context-khong-dong-bo/bug.md): lần đổi trước bị chặn và điều kiện làm lại.
- IPLMS PROB-034 (`docs/problems/09-2026/PROB-034-build-docker-nang-va-de-dut.md`, repo gốc).
