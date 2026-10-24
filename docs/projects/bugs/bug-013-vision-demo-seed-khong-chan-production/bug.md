# 🐛 bug-013: Nút nạp mẫu demo Vision Lab không chặn production, nạp lại lỗi 500 và nhãn kẹt bốn mắt

> **Đích:** `docs/projects/bugs/bug-013-vision-demo-seed-khong-chan-production/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code (rà code mới chưa commit trên `develop@534e0f8`) |
| **Trạng thái** | ✅ Fixed — chờ PR (nhánh `bugfix/bug-013-2026-10-vision-demo-seed-guard`) |
| **Môi trường** | local (code chưa merge) |

## Hành vi thực tế

Bản đầu của `POST /console/api/vision/seed-demo` (`seed_demo_samples`):

| # | Mức | Lỗi | Vị trí bản đầu |
|---|---|---|---|
| BUG-01 | 🔴 | Không chặn theo môi trường: ai có `ai:task:label` ở production cũng bơm 7 mẫu giả `purpose='train'` vào DB, đi thẳng vào snapshot train | `console_vision_controller.py` route `seed-demo` |
| BUG-02 | 🔴 | Nhãn mẫu chỉ `ON CONFLICT (id)`; mẫu đã có nhãn chờ duyệt/đã duyệt khác id → vướng `uq_vision_label_pending` → 500. `seeded_reviews` đếm cả khi `DO NOTHING` | `console_vision_store.py` vòng `seed_label` |
| BUG-03 | 🟠 | DB chỉ có một member (người bấm) → nhãn mẫu gán cho chính người bấm; `ck_vision_label_four_eyes` khiến không ai duyệt được, nhãn kẹt "chờ duyệt" | chọn `alt_labeler` fallback `members[0]` |
| BUG-04 | 🟠 | Sai phân tầng: `infra/` import `core/console/engines` và giữ dữ liệu demo trong store (AI_CONVENTIONS §1) | `console_vision_store.py:375` |
| BUG-05 | 🟡 | `ImageFont.load_default(size=)` cần Pillow ≥ 10.1, requirements ghim `>=10.0`; nhánh `electric` trùng nhánh mặc định | `demo_plate_generator.py` |
| BUG-06 | 🟠 | Không ghi `audit_event`, trái luật "mọi thao tác đổi trạng thái ghi audit trong CÙNG transaction" (docstring store) | `seed_demo_samples` |

## Hành vi mong đợi

Chỉ dev/sandbox nạp được; nạp lại bao nhiêu lần cũng không lỗi, không nhân bản; nhãn mẫu luôn của người khác người bấm để người bấm thực hành duyệt; có audit.

## Sửa / kiểm chứng

- Cờ `AI_CONSOLE_DEMO_SEED_ENABLED` (`app/config/console_config.py`, mặc định `False`), bật ở `docker-compose.develop.yml`, ghi `.env.example`; tắt → `ConsoleAccessDenied` (403) trước khi chạm DB (`vision_lab_service.py` `seed_demo_samples`).
- Dữ liệu `DEMO_SAMPLES` chuyển về engine `demo_plate_generator.py`; service dựng ảnh + SHA-256, store chỉ ghi (hết import ngược infra → core engine).
- Store: chọn người gán khác người bấm, không `DISABLED`; không có thì bỏ nhãn. Chèn nhãn có `WHERE NOT EXISTS` (chờ duyệt / đã duyệt / người này đã gán) + `ON CONFLICT DO NOTHING`, đếm bằng `rowcount`; ghi `audit_event` `vision.demo_seed`.
- `pillow>=10.1` ở cả hai requirements; gộp nhánh màu `electric`.

| Lệnh | Kết quả |
|---|---|
| `python -m unittest test.test_demo_plate_generator` (không DB) | ✅ 5/5 — gồm cờ tắt không gọi store |
| `AI_TEST_DATABASE_URL=… python -m unittest test.test_console_vision_lab test.test_demo_plate_generator test.test_console_vision_import test.test_console_http test.test_console_access` trên `pgvector/pgvector:pg16` tạm | 34/35 ✅; 1 ❌ `test_security_headers_and_no_docs` — đỏ cả trên `develop` chưa sửa, ghi [bug-014](../bug-014-console-docs-tra-spa-thay-vi-404/bug.md) |
| Test mới `test_nap_mau_demo_lap_lai_khong_loi_va_giu_bon_mat` | ✅ nạp 2 lần không lỗi (lần 2 `seeded_reviews=0`), người bấm duyệt được nhãn mẫu, có audit |

**Chưa làm:** chưa bấm thử nút trên UI `ai/ui` (UI chưa có nút gọi endpoint này trong diff); chưa chạy toàn bộ `test/`.
