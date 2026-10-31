# 🔎 audit-1: Convention audit — bug-029 sửa fallback DB tự tạo database

> Mẫu của [convention audit](../../../../../../skills/iplms-code-review/references/convention-audit.md) (ADR-0052). Auditor viết; fixer chỉ sửa cột "Đã sửa" và trạng thái `Fixed`; auditor đặt `Verified`/`Reopened` và Kết luận.

| | |
|---|---|
| **Kết luận** | ✅ Không còn P0–P2 mở (2026-10-26); còn 6 finding P3 `Open`, fixer chọn sửa hoặc `Deferred` |
| **Vòng** | 1/3 |
| **Phạm vi** | `ai`, nhánh `bugfix/bug-029-2026-10-db-fallback-tu-tao-database`, `git diff HEAD` (HEAD `844d5bd`, chưa stage) giới hạn ở 3 file: `app/infra/database/db_connection.py` (3 hunk), `test/test_db_connection_fallback.py` (file mới), `bug.md` (2 hunk). Các file khác trong working tree nằm ngoài phạm vi |
| **Auditor** | Claude, subagent convention audit, 2026-10-26. Không phải người viết code |
| **Fixer** | người thực thi bug-029 (@HiTranquility / agent được giao) |
| **Máy quét** | `check_diff.py --repo ai` (lệnh được giao) dừng hai lần vì git báo `Out of memory, malloc failed`; lệnh này bỏ qua `--repo` khi không có `--staged` nên quét cả 6 submodule. Đã chạy thay bằng `check_diff.py --root ai`, quét `ai` so với `origin/develop` (98 file code, gồm cả phạm vi này) → **0 FAIL, 0 WARN** |
| **Quy ước đã nạp** | `ai/docs/standards/AI_CONVENTIONS.md` §4 Config; `skills/iplms-code-review/references/convention-audit.md` §3; CLAUDE.md "Surgical Changes"; đặc tả bug-029 phần "Hành vi mong đợi" |

## Kết quả kiểm chứng

- `.venv/Scripts/python.exe -m unittest discover -s test` trong `ai/`: **PASS**, 567 test, OK (skipped=34).
- `unittest test.test_db_connection_fallback -v`: 4/4 PASS.
- Chạy lại cùng file với `AI_DB_HOST_PORT=5440`: **FAIL** 2/4. Với `AI_DB_HOST_PORT=5432`: **FAIL** 3/4. Xem A-2.
- Chưa chạy với Postgres thật có hai instance. Đây là gap runtime, giống `bug.md`.

## Các điểm người giao việc yêu cầu soát kỹ

| Câu hỏi | Kết luận | Bằng chứng |
|---|---|---|
| Ứng viên `host.docker.internal:5435` có bị coi nhầm là cổng của DB AI không? | Không coi là nhầm. Ứng viên này chỉ sinh khi có `/.dockerenv`. Cổng 5435 của host chính là cổng compose map cho DB AI (`docker-compose.yml:86` `${AI_DB_HOST_PORT:-5435}:5432`). Hàm chỉ so cổng, bỏ qua host, nhưng mọi ứng viên fallback đều là host local (`127.0.0.1`, `localhost`, `host.docker.internal`), nên cổng đủ phân biệt. Rủi ro còn lại: một Postgres lạ tự chiếm 5435 trên host. Trường hợp này nằm ngoài giả định của bug | `db_connection.py:53`, `:80-84`, `:95-99`, `:114-116` |
| Khi `AI_DB_HOST_PORT=5432` thì sao? | `own_port=5432`, nên mọi ứng viên local ở 5432 đều được tạo DB. Hành vi này nhất quán với khai báo "DB AI map ra 5432": compose và Postgres native không thể cùng giữ 5432, nên người đặt biến đã nói 5432 là DB AI. Khi đó 5435 lại bị chặn tạo DB, cũng đúng. Biến chỉ đọc từ môi trường của process, `.env` không nạp vào `os.environ` (xem A-4) | `db_connection.py:115` |
| `_redact_url` với URL không có mật khẩu | Trả nguyên URL. Không có bí mật nên không lộ gì. Còn hai kẽ (mật khẩu trong query, port hỏng) ghi ở A-5 | `db_connection.py:11-22` |
| `_RESOLVED_URL_CACHE` | Nhánh đọc cache (`:172-180`) chỉ `connect`, không bao giờ tạo DB. Cache chỉ ghi sau khi kết nối thành công (`:203`). Hunk không làm hỏng cache. Vấn đề nằm ở caller gán lại `self.db_url`, xem A-1 | `db_connection.py:172-180`, `:203` |
| Còn chỗ nào in URL thô không? | Không còn chỗ nào in mật khẩu. `:102` chỉ log `exc` của `urlsplit`. `:138` log hostname và port. `:143`, `:206-208`, `:218` đã qua `_redact_url`. `:218` thực tế không chạy tới được (xem A-3) | grep `logger\.` trong file |
| AI_CONVENTIONS §4 về `os.environ` | Hunk mới đọc `os.environ` tại `:115`, lặp lại cách parse của `:55`. Code cũ đã đọc như vậy và file nằm ở `infra`, không phải engine/service, nên chỉ ghi mức P3 (A-4) | AI_CONVENTIONS §4 |

## Findings

| # | Mức | Loại | `file:line` | Luật bị vi phạm | Mô tả | Cách sửa đề xuất | Trạng thái | Đã sửa |
|---|---|---|---|---|---|---|---|---|
| A-1 | P3 | đúng-sai | `app/infra/database/db_connection.py:112`; caller `console_store.py:51`, `pgvector_client.py:31`, `ai_request_log_store.py:31`, `knowledge_eval_store.py:102`, `model_policy_store.py:42` | bug-029 "Hành vi mong đợi": chỉ tạo DB khi ứng viên trùng **URL đã cấu hình** | Các store gán lại `self.db_url` bằng URL đã dùng được. Sau một lần fallback sang `127.0.0.1:5432` (DB đã có ở đó), lần gọi sau truyền chính URL 5432 làm `db_url`, nên `cand_url == db_url` cho phép tạo DB trên Postgres lạ. Chỉ xảy ra khi DB trên 5432 biến mất sau lần nối đầu, nên khó gặp | Ở caller, giữ URL cấu hình bất biến (biến riêng cho URL đã resolve), hoặc trong `_may_create_database` so với URL gốc lấy từ config/cache key thay vì tham số. Thêm một test gọi hai lần | Open | |
| A-2 | P3 | test | `test/test_db_connection_fallback.py:32-54` | convention-audit §3.4 (test phải chứng minh đúng điều cần chứng minh, ổn định) | Test phụ thuộc môi trường: không cô lập `AI_DB_HOST_PORT` và `/.dockerenv`. Đặt `AI_DB_HOST_PORT=5440` thì 2/4 fail, `=5432` thì 3/4 fail. Chạy trong container thì ứng viên đầu là `database-vector:5432`, nên assert `:5435/` ở `:47` sai. CI hiện không đặt biến này nên vẫn xanh | Dùng `patch.dict(os.environ, {"AI_DB_HOST_PORT": "5435"})` và `patch("os.path.exists", return_value=False)` trong `setUp`. Thêm một ca cho `AI_DB_HOST_PORT=5432` | Open | |
| A-3 | P3 | test | `test/test_db_connection_fallback.py:30`; `db_connection.py:217-219` | convention-audit §3.4 | `assertNotIn("pw-secret", str(ctx.exception))` đang kiểm thông điệp do mock tự dựng ("connection refused"), nên không chứng minh gì. Câu lỗi đã che ở `:217-219` không chạy tới được: `resolve_db_candidates` luôn trả ≥1 ứng viên nên `last_exc` luôn có. `bug.md` ghi test chứng minh "lỗi không chứa mật khẩu", như vậy là nói quá | Bỏ assertion vô nghĩa hoặc đổi thành kiểm `_redact_url` trực tiếp. Sửa câu trong `bug.md` cho đúng: test chỉ phủ phần log | Open | |
| A-4 | P3 | quy-ước | `app/infra/database/db_connection.py:115` (lặp `:55-59`) | [AI_CONVENTIONS §4](../../../../standards/AI_CONVENTIONS.md#4-config) [MUST] đọc config qua `get_config` | Đọc `AI_DB_HOST_PORT` thẳng từ `os.environ`, chép lại phần parse của `:55`. Hệ quả: native run đặt biến trong `.env` sẽ không thấy (pydantic `env_file` không nạp vào `os.environ`), nên `own_port` về 5435 và lệch với cổng compose thật | Tối thiểu: tách `_own_host_port()` dùng chung cho `:55` và `:115`. Đúng §4: thêm field vào một file config | Open | |
| A-5 | P3 | bảo-mật | `app/infra/database/db_connection.py:11-22` | — (gợi ý, không có luật cụ thể) | `_redact_url` không che mật khẩu nằm trong query (`?password=`, libpq có hỗ trợ). Khi `parsed.port` ném lỗi, hàm trả URL thô kèm mật khẩu. Đây là hàm cũ, nhưng hunk mới dựa vào nó cho log fallback | Trong nhánh `except`, trả chuỗi cố định (vd `"<url không hợp lệ>"`); che thêm khoá `password` trong query | Open | |
| A-6 | P3 | tài-liệu | `docs/projects/bugs/bug-029-…/bug.md:21` | doc-flow: hồ sơ khớp với hành vi đã sửa | "Hành vi mong đợi" vẫn ghi "chỉ khi trùng đúng URL cấu hình **và** bật cờ dev". Bản sửa cho thêm cổng `AI_DB_HOST_PORT` và không có cờ. Quyết định có ghi ở phần Sửa nhưng chưa nói rõ là lệch hai điểm của mục mong đợi | Thêm một dòng ở phần "Quyết định" nêu rõ lệch hai điểm (không có cờ, cho thêm cổng map) và lý do | Open | |

Trạng thái: `Open` → `Fixed` (fixer) → `Verified` (auditor) · `Reopened` · `Deferred` (P3, kèm hồ sơ theo dõi).

### Theo loại

| Loại | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| đúng-sai | 0 | 0 | 0 | 1 |
| test | 0 | 0 | 0 | 2 |
| quy-ước | 0 | 0 | 0 | 1 |
| bảo-mật | 0 | 0 | 0 | 1 |
| tài-liệu | 0 | 0 | 0 | 1 |

## WARN đã xét

Không có WARN (`check_diff.py --root ai`: 0 FAIL, 0 WARN).

## Bug đã mở

Không có. Không mở bug mới theo yêu cầu của người giao việc. A-1 là phần còn sót của chính bug-029.

## Ngoài phạm vi (nợ cũ nhìn thấy)

- `app/infra/database/db_connection.py:190-193`: chuỗi `"does not exist"` cũng khớp `role "x" does not exist`. Lỗi này vô hại vì `_ensure_database_exists` dùng cùng credential nên sẽ fail và trả False.
- `script/audit/check_diff.py:320`: khi không có `--staged`, script bỏ qua `--repo` và quét mọi submodule. Trên máy này lệnh đó gây OOM git.

## Soát lại

Mỗi vòng (lượt auditor) một dòng; tối đa 3 vòng, vòng 2–3 chỉ soát delta của fixer + finding `Fixed`. `Tree` = `git write-tree` của index lúc bắt đầu vòng (mỗi repo/submodule có diff một tree).

| Lần | Ngày | Tree | Finding đã soát | Kết quả |
|---|---|---|---|---|
| 1 | 2026-10-26 | `c80001fe5b41d6770d5e60c95dbaa22f8eeb8c64` (index = HEAD `844d5bd`; thay đổi chưa stage, vòng sau nên so `git diff c80001fe… -- <3 file>`) | Toàn bộ 3 file trong phạm vi | 0 P0–P2; A-1…A-6 P3 Open → ✅ |

## Đã sửa (fixer, sau vòng 1)

| # | Trạng thái | Đã sửa |
|---|---|---|
| A-2 | Fixed | `setUp` cô lập `AI_DB_HOST_PORT=5435` bằng `patch.dict` và patch `os.path.exists` (không phải container). Chạy lại với `AI_DB_HOST_PORT=5440`: 4/4 OK. |
| A-3 | Fixed | Bỏ assertion trên thông điệp do mock tự dựng; bug.md chỉ còn nói test log fallback không lộ mật khẩu. |
| A-6 | Fixed | "Hành vi mong đợi" trong bug.md ghi đúng luật đã làm (URL cấu hình hoặc cổng `AI_DB_HOST_PORT`, không cờ dev). |
| A-1, A-4, A-5 | Deferred | Ghi ở mục Sửa / kiểm chứng của bug.md. |
