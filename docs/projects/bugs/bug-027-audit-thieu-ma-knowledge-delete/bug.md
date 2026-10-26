# 🐛 bug-027: Thiếu mã kiểm toán `knowledge.delete` trong `auditActionCodes.json` và từ điển i18n làm gãy `test_console_audit_codes`

> **Đích:** `docs/projects/bugs/bug-027-audit-thieu-ma-knowledge-delete/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-25 / Dương (`@23110012`) |
| **Trạng thái** | ✅ Fixed |
| **Môi trường** | `develop@cc691e0` (local Docker + CI) |

## Hành vi thực tế

Khi chạy bộ kiểm thử toàn repo với Docker Postgres (`python -m unittest discover -s test`), `test/test_console_audit_codes.py` (`AuditActionCodesTest.test_moi_ma_server_co_trong_tu_dien_ui`) báo đỏ:

```
AssertionError: Lists differ: [] != ['knowledge.delete'] : Thêm các mã này vào auditActionCodes.json và i18n audit.actions
```

Nguyên nhân: commit `c6aa0b4` (PR #70) bổ sung hành động xoá tài liệu tri thức trong `app/core/console/services/tools_service.py` (`delete_knowledge_document`) có ghi nhật ký kiểm toán với mã `"knowledge.delete"`, nhưng chưa khai báo mã này trong `ui/src/pages/Audit/auditActionCodes.json` cũng như chưa thêm bản dịch tiếng Việt/tiếng Anh trong `ui/src/i18n/vi.ts` và `ui/src/i18n/en.ts`.

Ngoài ra, `.github/workflows/ci.yml` bước `Install CI dependencies` thiếu gói `pillow`, trong khi `app/console_main.py` nạp `app/core/vision/engines/demo_plate_generator.py` (`from PIL import Image, ImageDraw, ImageFont`).

## Hành vi mong đợi

- Mọi mã kiểm toán server ghi qua `_audit(...)` / `add_audit(...)` đều phải có trong `ui/src/pages/Audit/auditActionCodes.json` (thuộc nhóm hợp lệ `ml` / `rbac` / `auth` / `review`) và có nhãn hiển thị đầy đủ trong `ui/src/i18n/vi.ts` và `ui/src/i18n/en.ts`.
- `test/test_console_audit_codes.py` và `ui/src/pages/Audit/components/AuditActionBadge.test.tsx` đều PASS.
- Bước cài đặt phụ thuộc CI trong `.github/workflows/ci.yml` có `pillow>=10.0.0` để các test `test_console_http.py` và `test_demo_plate_generator.py` chạy ổn định.

## Tái hiện

1. Checkout `develop@cc691e0`.
2. Chạy `python -m unittest test.test_console_audit_codes -v`.
3. Quan sát lỗi `AssertionError: Lists differ: [] != ['knowledge.delete']` tại `test/test_console_audit_codes.py:47`.

## Bằng chứng

- `app/core/console/services/tools_service.py:187-190`: gọi `await self.store.add_audit(actor.member_id, "knowledge.delete", ...)`.
- `ui/src/pages/Audit/auditActionCodes.json:1-27`: chỉ có `"knowledge.ingest_draft": "ml"`, thiếu `"knowledge.delete"`.
- `ui/src/i18n/vi.ts:1000-1026` và `ui/src/i18n/en.ts:1021-1047`: thiếu khóa `'knowledge.delete'`.

## Sửa / kiểm chứng

Đã sửa trên nhánh `bugfix/bug-027-2026-10-audit-knowledge-delete-code`:

- Thêm `"knowledge.delete": "ml"` vào `ui/src/pages/Audit/auditActionCodes.json`.
- Thêm `'knowledge.delete': 'Xoá tài liệu tri thức'` vào `ui/src/i18n/vi.ts` và `'knowledge.delete': 'Knowledge document deleted'` vào `ui/src/i18n/en.ts`.
- Bổ sung `"pillow>=10.0.0"` vào `.github/workflows/ci.yml`.
- Kiểm chứng:
  - `python -m unittest test.test_console_audit_codes -v` -> PASS (3/3).
  - `npx vitest run src/pages/Audit/components/AuditActionBadge.test.tsx` -> PASS (4/4).
  - `pnpm --dir ui typecheck` -> PASS.
