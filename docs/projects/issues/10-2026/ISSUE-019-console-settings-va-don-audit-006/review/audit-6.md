# 🔎 audit-6: Convention audit — ISSUE-019 chặng 4 (A-7, A-22, A-37, A-41)

> Mẫu của [convention audit](../../../../../../../skills/iplms-code-review/references/convention-audit.md) (IPLMS ADR-0052). Auditor viết; fixer chỉ sửa cột "Đã sửa" và trạng thái `Fixed`; auditor đặt `Verified`/`Reopened` và Kết luận.
> Mô tả gốc của finding: [audit-2](audit-2.md), [audit-3](audit-3.md) (ở đó A-7 phần metrics, A-37, A-41 là `Deferred`, A-22 là "Cần quyết"). Vòng trước: [audit-5](audit-5.md). Hồ sơ: [ISSUE-019](../issue.md).

| | |
|---|---|
| **Kết luận** | ✅ Đạt (2026-10-26, vòng 1): không có P0–P2 Open/Reopened. A-7, A-22, A-37, A-41 Verified. Còn 4 P3 Open (A-70…A-73), không chặn. |
| **Vòng** | 1/3 (chặng 4 đếm vòng riêng) |
| **Phạm vi** | `ai/`, nhánh `feature/ISSUE-019-2026-10-console-settings-audit-006`, **phần đã stage** (`git -C ai diff --cached`): 14 file, +238/−55. Code: `app/config/embedding_config.py`, `app/infra/database/pgvector_client.py`, `app/infra/database/db_connection.py`, `app/script/seed_console_demo.py`, `app/core/console/services/copilot_lab_service.py`, `app/infra/llm/llm_factory.py`, `.env.example`. Test: `test/test_pgvector_fallback_flag.py` (mới), `test/test_console_copilot_lab.py`, `test/test_llm_factory.py`. Tài liệu: `DESIGN.md`, `docs/projects/adrs/10-2026/0001-fallback-khong-pgvector-chi-cho-dev.md` (mới), `issue.md` của ISSUE-018 và ISSUE-019. Bỏ qua phần chưa stage (`ui/**`, docs của phiên khác). |
| **Auditor** | Claude Code, subagent auditor độc lập, 2026-10-26. Không viết code chặng này. |
| **Fixer** | Claude Code (phiên điều phối) |
| **Máy quét** | `python -X utf8 script/audit/check_diff.py --staged --repo ai` (chạy từ gốc IPLMS) → 9 file code, **0 FAIL, 0 WARN** (auditor tự chạy lại, khớp số fixer báo). |
| **Quy ước đã nạp** | `ai/docs/standards/AI_CONVENTIONS.md` §1 (hướng phụ thuộc), §2 (import đầu file), §4 (config qua `get_config`, nhóm config theo file), §8 (`app/script/`) · `ai/DESIGN.md` bảng biến môi trường · `ai/docs/templates/adr-template.md` · IPLMS ADR-0049 (telemetry chỉ lưu bản đã che) · convention-audit §3.2 (hợp đồng), §3.4 (test chứng minh đúng điều cần chứng minh) |

## Kết quả chạy kiểm

| Lớp | Lệnh | Kết quả |
|---|---|---|
| Máy quét | `check_diff.py --staged --repo ai` | 0 FAIL, 0 WARN |
| Unittest đích | `ai/.venv/Scripts/python.exe -m unittest test.test_pgvector_fallback_flag test.test_console_copilot_lab test.test_llm_factory` | 25 test OK, 2 skip (cần `AI_TEST_DATABASE_URL`) |
| Unittest toàn bộ | `ai/.venv/Scripts/python.exe -m unittest discover -s test` | 569 OK, 34 skip (khớp số fixer báo). Không có phần `app/`/`test/` chưa stage, nên kết quả này ứng với đúng code đã stage. |
| DB thật | — | NOT RUN. Chưa chạy `seed_console_demo.py` và chưa dựng `PgVectorClient` trên Postgres thật (có và không có pgvector). Gap: A-7 và A-22 kết luận từ đọc code và test có mock. |
| Browser | — | Không áp dụng: chặng này không chạm UI. |

## Findings

| # | Mức | Loại | `file:line` | Luật bị vi phạm | Mô tả | Cách sửa đề xuất | Trạng thái | Đã sửa |
|---|---|---|---|---|---|---|---|---|
| A-7 | P2 | đúng-sai | `app/script/seed_console_demo.py:552`, `:556-558` | AI_CONVENTIONS §8; mô tả gốc ở audit-2 | (Phần metrics, `Deferred` ở audit-3.) Seed ghi đè `eval_run.metrics` bằng số bịa rồi propose/promote model. | Không ghi đè metrics; nếu cần dữ liệu demo thì ghi rõ là demo. | Verified | Đã bỏ `UPDATE eval_run` và bỏ `promote`. Chỉ còn `propose` với lý do `[DEMO]` trỏ tới `run_id`, note model gắn `[DEMO]`. `propose` vẫn đòi có lượt đo xong trên golden đã khoá (`model_lab_service.py:82-85`), và `start_eval` + `drain()` chạy trước đó (`:554-555`), nên luồng không gãy. Import `json` bỏ đi không còn chỗ dùng (grep `json.` = 0). |
| A-22 | — | quy-ước | `app/infra/database/pgvector_client.py:23`, `:99-107`; `app/config/embedding_config.py:44`; `.env.example:93` | Cổng schema; ai ADR-0001 | (Ở audit-3 là "Cần quyết".) Fallback `DOUBLE PRECISION[]` + `iplms_cosine_sim` chạy lặng lẽ khi thiếu pgvector. | Người dùng hoặc ADR quyết. | Verified | Chủ dự án chọn B, ghi ở [ADR-0001](../../../adrs/10-2026/0001-fallback-khong-pgvector-chi-cho-dev.md). Code khớp ADR: cờ `allow_no_pgvector` mặc định `False`, env `AI_EMBEDDING_ALLOW_NO_PGVECTOR` (prefix `AI_EMBEDDING_` ở `embedding_config.py:18`). Cờ tắt thì ném `RagPipelineError` trước mọi `CREATE` (trong `with connection:` nên rollback và nhả advisory lock), `_schema_ready` không bật nên lần sau báo lỗi lại. Cờ bật thì ghi `WARNING`. Đã kiểm lời ADR: CI (`.github/workflows/ci.yml:22`) và compose (`docker-compose.yml:74`) dùng `pgvector/pgvector`; không compose/deployment nào đặt cờ (grep toàn IPLMS). DESIGN `:273` có dòng biến mới. Test `test_pgvector_fallback_flag.py:23`, `:33`, `:43` kiểm cả ca từ chối (không có `CREATE TABLE`/`iplms_cosine_sim`), ca bật cờ và giá trị mặc định. |
| A-37 | P2 | bảo-mật | `app/core/console/services/copilot_lab_service.py:33-43`, `:144`, `:147`, `:161` | IPLMS ADR-0049 (telemetry chỉ lưu bản đã che); mô tả gốc ở audit-2 | (`Deferred` ở audit-3.) `var/eval_candidates.json` lưu câu hỏi thô, không có hạn lưu; audit summary chép `clean_query[:80]`. | Lưu bản đã redact như `ai_request_log`, có retention; bỏ câu hỏi khỏi audit summary. | Verified | `query` và `note` đi qua cùng `redact` của telemetry (`pii_redactor.py:18`). `_load_candidates` cắt mục cũ hơn `telemetry.retention_days` ở cả lúc đọc và lúc ghi. Audit summary chỉ còn hành vi kỳ vọng và category. Hình dạng phần tử trả về cho `GET` (`console_copilot_controller.py:124-127`) không đổi, chỉ nội dung đã che. Test `test_console_copilot_lab.py:92` kiểm biển số, SĐT, email không còn trong entry lẫn file thô, và summary không chứa câu hỏi; `:107` kiểm bỏ mục quá hạn. Fixer giữ file thay vì chuyển vào bảng DB (cách sửa gốc nêu hai ý; phần "bản đã redact + retention" đã đủ). Phần còn lại ghi ở A-73. |
| A-41 | P2 | hiệu-năng | `app/infra/llm/llm_factory.py:161-165`, `:207`, `:291`, `:326`, `:364`; `DESIGN.md:267` | AI_CONVENTIONS §4; mô tả gốc ở audit-2/audit-3 | (`Deferred` ở audit-3.) `urlopen` đồng bộ dò llama-server chạy trong đường async; việc bỏ auto-start chưa ghi DESIGN. | Dò ngoài event loop; ghi việc bỏ auto-start vào DESIGN. | Verified | `_aget_client` gọi `_get_client` qua `asyncio.to_thread`; cả 4 đường async đã đổi, grep không còn lời gọi `_get_client()` trực tiếp nào trong đường async. DESIGN `:267` ghi rõ AI không tự bật llama-server và dò `/health` ngoài event loop. Test `test_llm_factory.py:42` chứng minh `_get_client` chạy ở thread khác thread của loop (so `threading.get_ident()`, không chỉ khớp kết quả). Các tài liệu khác còn mô tả `ensure_server_running()` đã lên BOARD của ISSUE-019 (giao Khoa), không tính ở đây. Race lần tạo đầu ghi ở A-72. |
| A-70 | P3 | tài-liệu | `app/script/seed_console_demo.py:537` | CLAUDE.md "Surgical Changes" (comment phải khớp code đã đổi) | Comment đầu mục 3 vẫn ghi "… và Promote bản v1.0 lên Production", trong khi code đã bỏ `promote` (A-7). | Sửa comment thành "đăng ký model, đo trên golden đã khoá, chỉ đề xuất (demo)". | Open | |
| A-71 | P3 | đúng-sai | `app/script/seed_console_demo.py:564-567` | Cùng lý do A-7 (seed không dựng số liệu để ra quyết định). **Ngoài hunk**, ghi theo yêu cầu ở `issue.md:59`; không tính vào kết luận. | Mục 4 đề xuất chính sách ngưỡng với lý do tự đặt ("100% mẫu có độ tự tin >= 0.81 đều đọc chính xác…") rồi cho lead duyệt luôn. Seed đã bị chặn bởi cờ `demo_seed_enabled`, nên chỉ ảnh hưởng DB demo. | Gắn `[DEMO]` vào lý do, bỏ câu khẳng định số liệu; cân nhắc chỉ `propose`, để người dùng thử duyệt bốn mắt trên Console như A-7. | Open | |
| A-72 | P3 | hiệu-năng | `app/infra/llm/llm_factory.py:161-165` | — (gợi ý, không có luật) | Hai coroutine cùng gọi lần đầu khi `_client` còn `None` sẽ cùng chạy `_get_client` trong hai thread: dò `/health` hai lần, tạo hai `AsyncOpenAI` (một cái bị bỏ, không đóng), và cùng ghi `self.model`. Trước thay đổi, lời gọi đồng bộ nên không có race này. Tác động nhỏ vì chỉ xảy ra ở lần tạo đầu. | Bọc bằng `asyncio.Lock` và kiểm lại `_client` sau khi lấy khoá. | Open | |
| A-73 | P3 | bảo-mật | `app/core/console/services/copilot_lab_service.py:33-43` | — (gợi ý) | Hạn lưu chỉ áp khi có người đọc hoặc ghi file. Nếu không ai mở Copilot Lab, mục quá hạn vẫn nằm trên đĩa (đã che PII nên rủi ro thấp). Ngoài ra, che biển số làm ứng viên Eval mất giá trị cho các câu hỏi xoay quanh biển số; đây là đánh đổi chưa ghi ở đâu. | Ghi đánh đổi vào docstring hoặc DESIGN; nếu cần chặt thì cho job dọn telemetry dọn cả file này, hoặc chuyển vào bảng DB như cách sửa gốc. | Open | |

Trạng thái: `Open` → `Fixed` (fixer) → `Verified` (auditor) · `Reopened` · `Deferred` (P3, kèm hồ sơ theo dõi).
Loại: `quy-ước` · `hợp-đồng` · `đúng-sai` · `test` · `bảo-mật` · `hiệu-năng` · `tài-liệu`.

### Theo loại (Open + Reopened)

| Loại | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| đúng-sai | 0 | 0 | 0 | 1 (A-71) |
| bảo-mật | 0 | 0 | 0 | 1 (A-73) |
| hiệu-năng | 0 | 0 | 0 | 1 (A-72) |
| tài-liệu | 0 | 0 | 0 | 1 (A-70) |
| **Tổng** | **0** | **0** | **0** | **4** |

Verified vòng 1: A-7 (phần metrics), A-22, A-37, A-41.

## Hợp đồng hai đầu đã đọc

| Hợp đồng | Đầu gửi | Đầu nhận | Kết quả |
|---|---|---|---|
| Biến `AI_EMBEDDING_ALLOW_NO_PGVECTOR` | `.env.example:93`, `DESIGN.md:273` | `EmbeddingConfig.allow_no_pgvector` (`embedding_config.py:18`, `:44`) → `PgVectorClient.__init__` (`pgvector_client.py:23`) | Khớp tên, kiểu bool, mặc định `false` |
| `RagPipelineError` khi thiếu pgvector | `pgvector_client.py:100` | `ensure_schema` (`:70-76`) và các caller (`knowledge_eval_store.py:134`, `pgvector_client.py:40`, `:44`, `:314`) | Lỗi lan lên, `_schema_ready` không bật. Không caller nào nuốt lỗi để chạy tiếp ở chế độ mảng |
| Phần tử ứng viên Eval | `copilot_lab_service.py:142-150` | `console_copilot_controller.py:124-127` | Cùng khoá như trước; chỉ giá trị `query`/`note` đã che |
| `ConsoleModelLabService.propose` | `seed_console_demo.py:558` | `model_lab_service.py:77-86` | Cần lượt đo theo digest weights; seed chạy `start_eval` + `drain()` trước đó |

## WARN đã xét

Không có WARN.

## Bug đã mở

Không có. Không finding nào là lỗi chạy sai cần hồ sơ riêng (A-71 chỉ ảnh hưởng DB demo đã bị chặn bằng cờ).

## Ngoài phạm vi (nợ cũ nhìn thấy)

- `app/core/console/services/copilot_lab_service.py:42`, `:149`: `datetime.utcnow()` đã bị đánh dấu deprecated từ Python 3.12 (venv dùng 3.13). Dòng `:149` có từ trước; `:42` mới nhưng theo cùng kiểu. Không có luật trong AI_CONVENTIONS.
- `docs/projects/issues/10-2026/ISSUE-019-console-settings-va-don-audit-006/issue.md:43`: tiêu chí "P2 còn mở…" đã tick nhưng còn câu "**Chưa có auditor soát delta này**". Sau audit-6 thì câu này cần đổi thành trỏ tới audit-6; dòng BOARD "Soát PR ISSUE-019" (`:32`) cũng cần cập nhật trạng thái.

## Soát lại

Mỗi vòng (lượt auditor) một dòng; tối đa 3 vòng, vòng 2–3 chỉ soát delta của fixer + finding `Fixed`. `Tree` = `git write-tree` của index lúc bắt đầu vòng.

| Lần | Ngày | Tree | Finding đã soát | Kết quả |
|---|---|---|---|---|
| 1 | 2026-10-26 | `dcfc046baf570bac172896d015e34c0561082a33` | Toàn phần đã stage của chặng 4 (14 file): A-7, A-22, A-37, A-41 và hunk đi kèm | Verified 4. Mở A-70…A-73 (4 P3). Máy quét 0 FAIL, 0 WARN. Unittest 569 OK, 34 skip. |
