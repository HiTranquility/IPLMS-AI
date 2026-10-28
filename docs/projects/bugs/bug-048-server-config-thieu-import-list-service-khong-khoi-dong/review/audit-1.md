# 🔎 audit-1: Convention audit — bug-048 sửa import `typing` thiếu sau merge

> Mẫu của [convention audit](../../../../../../IPLMS/skills/iplms-code-review/references/convention-audit.md) (IPLMS ADR-0052). Auditor viết; fixer chỉ sửa cột "Đã sửa" và trạng thái `Fixed`; auditor đặt `Verified`/`Reopened` và Kết luận.

| | |
|---|---|
| **Kết luận** | ✅ Đạt (2026-10-28): không có finding P0–P2; 2 finding P3 tùy chọn |
| **Vòng** | 1/3 |
| **Phạm vi** | `iplms-ai`, staged trên `bugfix/bug-048-2026-10-server-config-thieu-import-list` (base `427c07f`); 5 file, 5 hunk (3 file code, 1 test mới, 1 bug.md) |
| **Auditor** | Claude Code, subagent convention audit — không phải người viết code |
| **Fixer** | Người thực thi bug-048 (chỉ khi chọn sửa P3) |
| **Máy quét** | `python3 -X utf8 script/audit/check_diff.py --staged --repo ../iplms-ai` (chạy từ IPLMS) → 0 FAIL, 0 WARN (lần 1) |
| **Quy ước đã nạp** | `AGENTS.md` (Stack và quy ước; Kiểm chứng: test `unittest`; Git và an toàn) · `docs/standards/AI_CONVENTIONS.md` §Public API của domain (import đầu file, AUDIT-006 A-1 `NameError`), §8 `app/script/` · `docs/templates/bug-template.md` |

## Kết quả soát từng hunk

| Hunk | AC / hành vi | Luật vùng | Hợp đồng | Test | Phần thừa |
|---|---|---|---|---|---|
| `app/config/server_config.py:2` thêm `from typing import List` | Đúng gốc lỗi: `List` dùng ở `:28` (`cors_allow_origin_list`), file không có `from __future__ import annotations` → `NameError` khi tạo class | Import đầu file, khớp AI_CONVENTIONS §Public API | Không đổi chữ ký/kiểu trả về | Phủ bởi `test_every_app_module_imports_typing_names_it_uses` | Không |
| `app/core/console/services/tools_service.py:13` thêm `List` | `List` dùng ở `:399`, `:418` | Như trên | Không đổi | Phủ | Không |
| `app/core/copilot/engines/rag_pipeline.py:6` thêm `List, Optional` | Dùng ở `:103`, `:122`, `:344`, `:387`; module có `from __future__` nên chỉ là F821, sửa cho nhất quán đúng phạm vi bug.md | Như trên | Không đổi | Phủ | Không |
| `test/test_typing_imports.py` (mới) | Test hồi quy đúng điều cần chứng minh: quét AST toàn `app/`, so `offenders == {}` (kiểm kết quả, không khớp tiền tố) | `unittest` theo AGENTS.md Kiểm chứng; đặt ở `test/`, không ở `app/script/` (§8) | — | Auditor chạy lại 2/2 OK; chạy hàm `missing_typing_imports` trên bản `git archive 427c07f app` → đúng 3 file (`config/server_config.py` [List], `console/services/tools_service.py` [List], `copilot/engines/rag_pipeline.py` [List, Optional]), khớp claim "FAIL trên develop" | Không |
| `docs/projects/bugs/bug-048-…/bug.md` (mới) | Gốc lỗi có commit (`f7ff908` → `4a27ba1`), tái hiện, phần chưa chạy ghi rõ | Mã bug-048 không trùng (bug-047 đã dùng ở nhánh chore, được ISSUE-022 trỏ tới) | — | — | Xem A-1 |

## Findings

| # | Mức | Loại | `file:line` | Luật bị vi phạm | Mô tả | Cách sửa đề xuất | Trạng thái | Đã sửa |
|---|---|---|---|---|---|---|---|---|
| A-1 | P3 | tài-liệu | `docs/projects/bugs/bug-048-server-config-thieu-import-list-service-khong-khoi-dong/bug.md:7-13,29` | [bug-template](../../../../templates/bug-template.md) (Meta + mục `## Bằng chứng`) | Meta thiếu dòng `Hạn`; không có mục `## Bằng chứng` (bằng chứng `file:line`/commit đang nằm trong "Hành vi thực tế"). Không ảnh hưởng BOARD vì `Hạn` không bắt buộc; bug-046 cũng bỏ `Hạn`. | Tùy chọn: tách đoạn "Gốc: commit …" thành `## Bằng chứng`; thêm `Hạn` nếu có. | Open | |
| A-2 | P3 | test | `test/test_typing_imports.py:12,15-24` | Không có luật cụ thể — gợi ý (convention-audit §3 bước 4) | (a) `_bound_names` gom tên bind ở mọi scope của module, nên `from typing import List` cục bộ trong một hàm sẽ che việc dùng `List` ở mức module/class; (b) `TYPING_NAMES` chỉ có 9 tên, bỏ sót `Sequence`, `Type`, `Literal`, `Mapping`, `AsyncGenerator`… Test vẫn bắt đúng lớp lỗi của bug-048. | Tùy chọn: chỉ tính import ở mức module (`tree.body`) và mở rộng `TYPING_NAMES` (hoặc lấy `typing.__all__`). Có thể hoãn. | Open | |

Trạng thái: `Open` → `Fixed` (fixer) → `Verified` (auditor) · `Reopened` · `Deferred` (P3, kèm hồ sơ theo dõi).

### Theo loại

| Loại | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| tài-liệu | 0 | 0 | 0 | 1 |
| test | 0 | 0 | 0 | 1 |

## WARN đã xét

Không có WARN.

## Bug đã mở

Không có. Lỗi chạy sai duy nhất là chính bug-048.

## Ngoài phạm vi (nợ cũ nhìn thấy)

Không có.

## Gap (cần runtime, chưa chạy)

- Khởi động service thật (gRPC + FastAPI) và bộ `python -m unittest discover -s test -t .` đầy đủ: NOT RUN vì chưa cài `requirements.txt` (người thực thi đã ghi trong bug.md). Auditor chỉ đọc code + chạy `test.test_typing_imports`; không chạy browser/DB.
- Chưa có lint F821 (ruff/pyflakes) trong CI để chặn lớp lỗi này ở lần merge sau; test AST đang làm thay. Không có luật nào yêu cầu, chỉ là gợi ý.

## Soát lại

| Lần | Ngày | Tree | Finding đã soát | Kết quả |
|---|---|---|---|---|
| 1 | 2026-10-28 | `7a60921525c977c90f09778b4bb0884c9f4603ea` | toàn diff staged | 0 P0–P2; A-1, A-2 (P3) Open |
