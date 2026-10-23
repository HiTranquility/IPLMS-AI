# 🔎 audit-1: Convention audit — bug-013 chặn production cho nạp mẫu demo Vision Lab

> Mẫu của [convention audit](../../../../../../skills/iplms-code-review/references/convention-audit.md) (IPLMS ADR-0052). Auditor viết; fixer chỉ sửa cột "Đã sửa" và trạng thái `Fixed`; auditor đặt `Verified`/`Reopened` và Kết luận.

| | |
|---|---|
| **Kết luận** | ✅ Đạt sau soát lại (2026-10-23) — A-1…A-7 Verified, không còn finding mở |
| **Vòng** | 3/3 |
| **Phạm vi** | submodule `ai`, staged trên nhánh `bugfix/bug-013-2026-10-vision-demo-seed-guard`; 13 file (10 file code + 2 hồ sơ bug), +340/−3 |
| **Auditor** | Claude Code (subagent auditor độc lập, 2026-10-23), không phải người viết code |
| **Fixer** | Claude Code (người thực thi, 2026-10-23) — test sau sửa: `test_demo_plate_generator` + `test_console_vision_lab` + `test_console_vision_import` + `test_console_access` trên Postgres tạm: 35/35 OK |
| **Máy quét** | `python -X utf8 script/audit/check_diff.py --staged --repo ai` → 0 FAIL, 0 WARN (lần 1, auditor chạy lại) · 0 FAIL, 0 WARN (soát lại vòng 2) · 0 FAIL, 0 WARN (soát lại vòng 3) |
| **Quy ước đã nạp** | `ai/docs/standards/AI_CONVENTIONS.md` §1 (phân tầng), §2 (engine/service), §4 (config), §5 (hai requirements); `ai/DESIGN.md` dòng 11 (ngoại lệ AI Console) và dòng 30 (ma trận môi trường); `ai/AGENTS.md` mục Stack ("cập nhật DESIGN và ngoại lệ cùng thay đổi"); `AGENTS.md` gốc mục Submodule; `.claude/rules/supply-chain.md`; `skills/iplms-doc-flow/SKILL.md` mục "Lên BOARD cùng lượt"; [convention-audit](../../../../../../skills/iplms-code-review/references/convention-audit.md) §3.4 |

## Findings

| # | Mức | Loại | `file:line` | Luật bị vi phạm | Mô tả | Cách sửa đề xuất | Trạng thái | Đã sửa |
|---|---|---|---|---|---|---|---|---|
| A-1 | P2 | test | `test/test_demo_plate_generator.py:45-55`; đường thật ở `app/core/console/services/vision_lab_service.py:102-106` | [convention-audit §3.4](../../../../../../skills/iplms-code-review/references/convention-audit.md) (test phải chứng minh đúng điều cần chứng minh) | AC chính của bug-013 (BUG-01 🔴) là "production mặc định không nạp được". Production dùng singleton `console_vision_lab_service` dựng không tham số, nên cờ được đọc từ `get_config().console.demo_seed_enabled` (dòng 104). Cả hai test guard đều tiêm `demo_seed_enabled=True/False` vào constructor nên **không bao giờ đi qua nhánh `enabled is None`**. Nếu ai đó đổi mặc định `ConsoleConfig.demo_seed_enabled` hoặc gõ sai tên field, test vẫn xanh. | Thêm một test dựng `ConsoleVisionLabService(store=_Store())` không truyền cờ, với `AI_CONSOLE_DEMO_SEED_ENABLED` không đặt (hoặc patch `get_config` trả `ConsoleConfig()` mặc định), rồi assert `ConsoleAccessDenied` và `store.calls == []`. Có thể thêm một ca `ConsoleConfig().demo_seed_enabled is False`. | Verified | `test_khong_truyen_co_thi_doc_config_mac_dinh_tat` (service không truyền cờ, gỡ env → 403, store không bị gọi) |
| A-2 | P2 | tài-liệu | `ai/DESIGN.md:11`; `app/infra/database/console_vision_store.py:3-4` | `ai/AGENTS.md` mục Stack và quy ước ("cập nhật DESIGN và ngoại lệ cùng thay đổi"); `AGENTS.md` gốc mục Submodule ("Đổi kiến trúc… hoặc môi trường phải cập nhật DESIGN cùng code"); `AI_CONVENTIONS.md` dòng 12 | Diff thêm (1) đường ghi thứ hai vào `vision_sample`/`vision_crop`/`vision_label` ngoài kênh A2 và (2) cờ môi trường khác nhau giữa develop (bật) và base/production (tắt). DESIGN dòng 11 vẫn mô tả dữ liệu Vision chỉ đến từ A2; docstring store dòng 3 vẫn ghi `vision_sample` + `vision_crop` là "bản sao CHỈ ĐỌC từ backend qua kênh A2". Cả hai giờ đều sai, trong khi đây chính là điều người vận hành cần biết để không bật cờ ở production. | Trong DESIGN dòng 11 (ngoại lệ AI Console), thêm một câu: nút/endpoint `POST /console/api/vision/seed-demo` ghi 7 mẫu `purpose='train'` khi `AI_CONSOLE_DEMO_SEED_ENABLED=true` (chỉ compose develop; base/production mặc định tắt, tắt thì 403). Sửa docstring store dòng 3: "bản sao từ backend qua A2; ngoại lệ dev: `seed_demo_samples`". | Verified | `ai/DESIGN.md` thêm đoạn "Ngoại lệ dev/sandbox — mẫu thực hành Vision Lab"; docstring `console_vision_store.py:3-6` ghi ngoại lệ |
| A-3 | P3 | tài-liệu | `docs/projects/BOARD.md` (thiếu dòng) | [doc-flow · Lên BOARD cùng lượt](../../../../../../skills/iplms-doc-flow/SKILL.md) | Tạo bug-013 (✅ Fixed, chờ PR) và bug-014 (🆕 New) nhưng `ai/docs/projects/BOARD.md` không có dòng nào cho hai hồ sơ này (grep `bug-013`/`bug-014` chỉ trúng một dòng `IPLMS bug-014` của repo gốc, khác hồ sơ). `check_drift.py --board` sẽ WARN. | Thêm dòng bug-013 vào 🚧 (hoặc ✅ kèm ngày khi merge), dòng bug-014 vào 🙋 với ưu tiên 🟡/🟢 theo hồ sơ. | Verified | BOARD: bug-013 ở 🚧 Đang làm, bug-014 ở 🙋 Cần người nhận |
| A-4 | P3 | test | `test/test_console_vision_lab.py:135-149` | [convention-audit §3.4](../../../../../../skills/iplms-code-review/references/convention-audit.md) | Test DB chỉ phủ "nạp lại khi nhãn còn chờ duyệt". Hai nhánh mà bug.md nêu là đã sửa nhưng chưa có test: BUG-03 khi DB chỉ có người bấm (`labeler_id is None`, store dòng 379-382, phải bỏ nhãn, `seeded_reviews=0`) và BUG-02 nạp lại sau khi nhãn mẫu đã được APPROVED (nhánh `decision = 'APPROVED'` trong `WHERE NOT EXISTS`). | Thêm hai ca: schema chỉ có một member thì nạp xong `seeded_reviews == 0` và không lỗi; sau khi `decide(... "APPROVED")` thì nạp lại không lỗi và `seeded_reviews == 0`. | Verified | thêm assert nạp lại sau APPROVED (`seeded_reviews=0`) + `test_nap_mau_demo_khi_khong_co_nguoi_khac_thi_bo_nhan` |
| A-5 | P3 | quy-ước | `app/infra/database/console_vision_store.py:394` | Không có luật cứng; gợi ý: đường import A2 dùng `make_interval(days => retention_days)` lấy từ `ConsoleConfig.vision_retention_days` (store dòng 241) | Mẫu demo ghi cứng `NOW() + interval '90 days'`, lệch với cấu hình `AI_CONSOLE_VISION_RETENTION_DAYS` mà đường import dùng. Đổi retention thì mẫu demo không theo. | Service truyền `retention_days` từ `get_config().console.vision_retention_days` xuống store, giống `vision_import_service`. | Verified | store nhận `retention_days`, service truyền `ConsoleConfig.vision_retention_days`, SQL `make_interval(days => %s)` |
| A-6 | P3 | bảo-mật | `app/infra/database/console_vision_store.py:376-382`, `:429-430` | Không có luật cứng; gợi ý theo docstring store dòng 9 (audit trong cùng transaction) | Nhãn mẫu được ghi `labeler_id` = một member thật khác (member cũ nhất chưa `DISABLED`), dù người đó không gán. Audit `vision.demo_seed` chỉ ghi số lượng, không ghi nhãn mẫu được gán cho ai, nên đọc audit không phân biệt được nhãn mẫu với nhãn thật của người đó. Chỉ chạy khi cờ bật (dev/sandbox), nên mức P3. | Ghi `labeler_id` được chọn (và danh sách `label_id` mẫu) vào `reason` của audit `vision.demo_seed`. | Verified | reason audit ghi id thành viên đứng tên nhãn mẫu ("người này không tự gán") |
| A-7 | P3 | test | `test/test_demo_plate_generator.py:57-68` | [convention-audit §3.4](../../../../../../skills/iplms-code-review/references/convention-audit.md) | Mới ở vòng 2, nằm trong delta của fixer. Test đã đi qua nhánh `enabled is None` → `get_config()`, nên sai tên field sẽ làm test đỏ; vì vậy A-1 đạt. Tuy nhiên `mock.patch.dict(os.environ, …)` gần như vô tác dụng: `get_config` có `@lru_cache` (`app/config/app_config.py:34`) và đã được gọi lúc import, vì singleton store gọi `get_config()` ở `console_store.py:42`. Ngoài ra `BaseConfig` còn đọc `env_file=.env.dev` (`base_config.py:7`). Kết quả: test phản ánh cấu hình thật của máy đang chạy, không phải mặc định. CI không có `.env.dev` thì vẫn đúng; máy dev có `AI_CONSOLE_DEMO_SEED_ENABLED=true` trong `.env.dev` thì test đỏ giả. | Patch `vision_lab_service.get_config` để trả object có `console=ConsoleConfig(_env_file=None)` (hoặc assert thẳng `ConsoleConfig(_env_file=None).demo_seed_enabled is False`), rồi bỏ đoạn patch env. | Verified | patch `vision_lab_service.get_config` trả `ConsoleConfig(_env_file=None)` dựng khi đã gỡ env; xanh cả khi chạy với `AI_CONSOLE_DEMO_SEED_ENABLED=true` |

Trạng thái: `Open` → `Fixed` (fixer) → `Verified` (auditor) · `Reopened` · `Deferred` (P3, kèm hồ sơ theo dõi).
Loại: `quy-ước` · `hợp-đồng` · `đúng-sai` · `test` · `bảo-mật` · `hiệu-năng` · `tài-liệu`.

### Theo loại

| Loại | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| test | 0 | 0 | 1 | 2 |
| tài-liệu | 0 | 0 | 1 | 1 |
| quy-ước | 0 | 0 | 0 | 1 |
| bảo-mật | 0 | 0 | 0 | 1 |
| hợp-đồng | 0 | 0 | 0 | 0 |
| đúng-sai | 0 | 0 | 0 | 0 |

### Đã soát, không thành finding

- **Phân tầng (§1):** route chỉ gọi `console_vision_lab_service` (không import engine); service import engine `demo_plate_generator` và `get_config`; store không còn import ngược `core/` (BUG-04 đã hết). Domain `console` đủ `dtos/engines/services` (§2). Service chỉ giữ cờ cấu hình, không giữ trạng thái nghiệp vụ.
- **Config (§4):** cờ nằm trong `console_config.py` (`env_prefix="AI_CONSOLE_"`), đọc qua `get_config()`, không đọc `os.environ`; `.env.example` có dòng mặc định `false`.
- **Hợp đồng hai đầu:** khoá `SeedResult` (`seeded_samples`, `seeded_reviews`) khớp dict store trả về (store dòng 431); `ConsoleAccessDenied` được map 403 ở `app/console_main.py:44`; `verdict` mẫu (`CORRECT`, `CORRECTED`) nằm trong `ck_vision_label_verdict` (store dòng 108); `group_ref`/`area_ref` dài đúng 64 ký tự cho `CHAR(64)`; quyền `ai:task:label` khớp route `add_label`.
- **Compose:** `docker-compose.develop.yml` thêm `environment` dạng list, gộp theo tên biến với list ở `docker-compose.yml:115`; `docker-compose.production.yml` không có service `console`, nên production dùng mặc định `False`.
- **Requirements (§5, supply-chain):** `pillow` đã có sẵn, chỉ nâng sàn lên `>=10.1` (cần cho `ImageFont.load_default(size=)`) và nâng ở cả hai file; không thêm package mới.

## WARN đã xét

Không có WARN (máy quét 0 FAIL, 0 WARN).

## Bug đã mở

Không có. Không finding nào là lỗi chạy sai. bug-014 (console `/docs` trả SPA) đã do người thực thi mở, ngoài phạm vi audit này.

## Ngoài phạm vi (nợ cũ nhìn thấy)

- `test/test_console_http.py:134` đỏ trên `develop` (đã ghi ở bug-014), không tính vào kết luận.

## Gap (cần runtime, chưa chạy)

- Auditor chỉ đọc code và chạy `check_diff.py`. Chưa chạy lại unittest, chưa gọi endpoint thật, chưa mở browser.
- Diff không có UI gọi `POST /console/api/vision/seed-demo` (grep `ui/src` không trúng), dù comment ở config, compose và `.env.example` đều nói về "nút nạp mẫu thực hành". Câu hỏi cho người thực thi: nút nằm ở nhánh/hồ sơ khác (ISSUE-126?) hay chưa làm? Nếu chưa làm thì cần ghi vào mục "Chưa làm" của bug.md cho rõ.
- Các lớp L1–L8 của cổng chất lượng (browser viewport × theme, a11y) chưa áp dụng được vì không có UI trong diff.

## Soát lại

Mỗi vòng (lượt auditor) một dòng; tối đa 3 vòng, vòng 2–3 chỉ soát delta của fixer + finding `Fixed`. `Tree` = `git write-tree` của index lúc bắt đầu vòng (mỗi repo/submodule có diff một tree).

| Lần | Ngày | Tree | Finding đã soát | Kết quả |
|---|---|---|---|---|
| 1 | 2026-10-23 | `22cdceaec3e096fec62096fc4f3e390e4351a39f` (ai) | Toàn bộ diff staged | 6 Open (2 P2, 4 P3) |
| 2 | 2026-10-23 | `8211d58ba79f6b8c59e8d0be61aeb0fa39fecf1f` (ai) | A-1…A-6 (Fixed) + delta 6 file so với `22cdcea` | A-1…A-6 Verified; mở A-7 (P3, test) |
| 3 | 2026-10-23 | `660d8164ead31f338e0f24a3d68007159934ad2f` (ai) | A-7 (Fixed) + delta `test/test_demo_plate_generator.py` so với `8211d58` | A-7 Verified: config dựng khi env đã gỡ + `_env_file=None`, patch đúng `vision_lab_service.get_config`, vẫn đi nhánh `enabled is None` |
