# 🐛 bug-053: `database-vector` chết ở lần init đầu, clone riêng không build được, CI có mật khẩu literal

> **Đích:** `docs/projects/bugs/bug-053-db-init-hong-va-build-can-repo-cha/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🛠️ Fixing |
| **Người nhận** | HiTranquility |
| **Hạn** |  |
| **Ưu tiên** | 🔴 |
| **Ngày đóng** |  |
| **Ngày báo** | 2026-10-31 |
| **Người báo** | Claude Code, lượt rà IPLMS-AI trước nộp Final (2026-10-31) |
| **Môi trường** | local Docker (`docker-compose.develop.yml`), `main` `82af07f` và `develop` `fa3ea51` |

## Hành vi thực tế

1. **🔴 DB không lên.** Chạy compose lần đầu (volume `database-vector-data` trống, có `AI_CONSOLE_DB_PASSWORD`): container `database-vector` thoát code 3, nên `api` và `console` (đều `depends_on: service_healthy`) không bao giờ chạy.
   - `docker/database-vector/init/11-ai-inference-role.sh` truyền mật khẩu bằng `psql -v pw=...` rồi dùng `:'pw'` **bên trong** khối `DO $$ … $$`. psql không thay biến trong chuỗi dollar-quoted, nên server nhận nguyên `:'pw'` và báo `ERROR: syntax error at or near ":"`.
   - File có mode `100644` (file `10-…` là `100755`), nên entrypoint Postgres *source* nó vào chính shell của entrypoint thay vì chạy riêng (log: `sourcing /docker-entrypoint-initdb.d/11-ai-inference-role.sh`). Nhánh `exit 0` khi console tắt khi đó sẽ thoát luôn entrypoint.
2. **🟠 Clone riêng không build được.** `docker-compose.yml` khai `context: ..` và `Dockerfile` `COPY ai/... proto`, nên clone `IPLMS-AI` một mình rồi `docker compose up --build` thì lỗi. README không nói phải clone repo cha. Đề Final §9 đòi README "how to run".
3. **🟠 Mật khẩu literal.** `.github/workflows/ci.yml` có mật khẩu Postgres viết thẳng (dòng 25, 35–40, 70–71), cùng giá trị nằm trong lịch sử Git từ commit `2c383f0` (2026-09-25). Đề Final §11: secret trong lịch sử Git bị trừ 5% điểm nhóm.

## Hành vi mong đợi

- Volume trống: init chạy hết, `database-vector` healthy, role `ai_inference` đăng nhập được DB `ai_console`.
- `git clone https://github.com/HiTranquility/IPLMS-AI.git` → `docker compose … up --build` chạy được, không cần repo cha.
- Không còn mật khẩu literal trong repo.

## Tái hiện

1. `cp .env.example .env.dev`, điền `AI_DB_PASSWORD`, `AI_CONSOLE_DB_PASSWORD`, `AI_INFERENCE_DB_PASSWORD`.
2. `docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.develop.yml up -d database-vector` (volume trống).
3. `docker logs <project>-database-vector-1` → `ERROR: syntax error at or near ":" at character 143`; `docker ps -a` → `Exited (3)`.

## Bằng chứng

- Log container (2026-10-31): `sourcing /docker-entrypoint-initdb.d/11-ai-inference-role.sh` → `ERROR: syntax error at or near ":" at character 143`.
- `git ls-files -s docker/database-vector/init` → `100644 … 11-ai-inference-role.sh`.
- Mật khẩu: `git log --all -S<giá trị>` = 7 commit (2026-10-31, đếm trên `main`, `develop`, `bugfix/bug-050` và các tag `archive/*`). Giá trị không ghi ở đây.

## Sửa / kiểm chứng

| Thay đổi | File |
|---|---|
| Dựng `CREATE/ALTER ROLE` bằng `SELECT format('… %L', :'pw') … \gexec`; `chmod +x` | `docker/database-vector/init/11-ai-inference-role.sh` |
| Job CI `db-init`: chạy pgvector với thư mục init trên volume trống, đợi `init process complete`, kiểm `ai_inference` đăng nhập | `.github/workflows/ci.yml` |
| Mật khẩu CI thành `ci-${{ github.run_id }}-${{ github.run_attempt }}` (DB chỉ sống trong job) | `.github/workflows/ci.yml` |
| Build context = repo này ([ADR-0006](../../adrs/10-2026/0006-build-context-la-repo-ai.md)); một allowlist `.dockerignore` | `Dockerfile`, `.dockerignore`, `docker-compose*.yml`, `.github/workflows/image.yml`, `test/test_docker_context.py`, README, SETUP_GUIDE, DESIGN, AI_CONVENTIONS §7, `proto/README.md` |

Kiểm chứng (2026-10-31, sandbox cloud):

- Các bước của job `db-init` chạy ở local: script cũ (`origin/develop`) → **FAIL** đúng lỗi `syntax error at or near ":"`; script mới → **PASS**, `ai_inference` đăng nhập được.
- `AI_RUN_CONTEXT_FIXTURE=1 python -m unittest test.test_docker_context` → OK.
- Build probe từ `git archive` của nhánh (không có repo cha), giữ nguyên các lệnh COPY + `compile_proto.py` của `Dockerfile`: đủ 7 cặp stub, có `data/prompts/{copilot_rag_system,eval_generator,eval_judge,redteam_attacker}`, `/app` chỉ có `app data model proto static var`.
- YAML của `ci.yml`, `image.yml` và hai file compose parse được; `docker compose config -q` OK.
- **Chưa chạy:** build image đầy đủ (sandbox chặn `deb.debian.org` và `download.pytorch.org`), job `db-init` trên GitHub Actions (chạy khi mở PR).
- **Chưa xử lý trong nhánh này:** xem bảng dưới. Kiểm IPLMS gốc (2026-10-31), giá trị đọc từ một file cục bộ, không ghi vào lệnh hay vào repo: `git grep -lF -f <file-giá-trị> origin/main` (`741a6f4`) ra 2 file, `docs/guides/10-2026/secrets-setup-and-checklist.md` và `docs/standards/devops/SECRETS_MANAGEMENT.md`, nơi giá trị được dùng làm mật khẩu local mẫu; trên `origin/develop` ra 0 file; `git log --all -S` ra 4 commit. Chuỗi phải khớp **đúng từng ký tự** của literal trong `ci.yml` cũ (dòng `PGPASSWORD=`, bỏ hậu tố nếu có). Grep một giá trị đoán thì ra 0, là kết quả âm tính giả.

## 📋 Việc trên BOARD

| Việc | Người nhận | Hạn | Ưu tiên | Trạng thái |
|---|---|---|---|---|
| Viết lại lịch sử Git IPLMS-AI để xoá mật khẩu cũ (mọi nhánh + tag) rồi force push | HiTranquility |  | 🔴 | ✅ 2026-10-31: chủ repo chạy `evidence/clean_history.sh --push` (59 chỗ thay, 4 nhánh + 5 tag). Kiểm bằng clone mirror mới: 0 lần trên mọi nhánh/tag và commit message |
| Nhờ GitHub Support xoá các ref `refs/pull/*` của PR cũ còn trỏ tới commit cũ (36 lần xuất hiện) và cache; repo hiện private | HiTranquility |  | 🟠 | 🆕 New |
| Đổi mật khẩu ở mọi DB/máy từng dùng giá trị cũ | HiTranquility |  | 🔴 | 🆕 New |
| Sửa `backend/docker-compose.yml` (service AI build) sang `context: ../ai`, `dockerfile: Dockerfile`, trước khi nâng gitlink `ai` ở umbrella (ADR-0006 › Caller) | HiTranquility |  | 🔴 | 🛠️ HiTranquility/IPLMS-Backend#65 (nhánh cùng tên); merge cùng #127 rồi mới nâng gitlink |
| Sửa `deployment/registry/push-images-local.{ps1,sh}` và `operations.md:267` sang context `ai/` | HiTranquility |  | 🟠 | 🛠️ HiTranquility/IPLMS-Deployment#17 |
