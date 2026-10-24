# 🐛 bug-020: Trang Nhật ký dùng mã hành động `ai:…` nhưng server ghi `member.invite`, `role.grant:<vai>`…, nên nhãn, nhóm và số đếm đều sai

> **Đích:** `docs/projects/bugs/bug-020-audit-tu-dien-hanh-dong-lech-server/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code, rà UI trong [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) |
| **Trạng thái** | ✅ Fixed (chờ PR) / 🟡 |
| **Môi trường** | `develop@5f8e753` |

## Hành vi thực tế

`ACTION_METAS` khai khoá dạng `ai:member:invited`, `ai:role:granted`, `ai:golden:freeze`… Server không ghi khoá nào có dạng này. Code server ghi `member.invite`, `role.grant:<vai>`, `role.revoke:<vai>`, `snapshot.create:<loại>`, `snapshot.freeze`, `policy.propose`, `policy.approved|rejected`, `model.register|propose|promote|retire`, `eval.start`, `copilot.review:<kết luận>`, `knowledge.ingest_draft:<trạng thái>`, `vision.demo_seed`, `auth.*` và `system.bootstrap_admin`. Vì vậy:

- Không có hành động nào được dịch: badge hiện mã thô, và không bao giờ có nhãn EN (`labelEn` không được dùng).
- Nhóm hoá dựa vào chuỗi con. `snapshot.freeze` (khoá golden) và `snapshot.create:*` không chứa "golden" hay "dataset", nên rơi vào nhóm `other`. Ô "MLOps & dữ liệu" vì thế đếm thiếu, bộ lọc nhóm cũng không tìm ra hai hành động này.
- `copilot.review:*`, `eval.start`, `knowledge.*`, `vision.demo_seed` không thuộc nhóm nào có trong bộ lọc.

## Hành vi mong đợi

Từ điển dùng đúng mã server ghi, khớp theo tiền tố trước `:`. Nhãn lấy từ i18n (`vi.ts`/`en.ts`). Có test đối chiếu danh sách mã ở server với từ điển, để thêm mã mới mà quên khai thì test báo đỏ.

## Tái hiện

1. Mở `/audit`. Mock trả `role.grant`, `member.invite`, `label.decide`, `policy.propose`, mỗi loại 7-8 dòng, tổng 30. Kết quả: badge hiện mã thô; ô "MLOps & dữ liệu" = 7, tức chỉ đếm `policy.propose` ([ảnh](../../issues/10-2026/ISSUE-004-ai-console-ui-review/evidence/06-audit.png)).
2. `grep -rn "_audit(" app/infra/database/console*.py app/core/console/services` liệt kê mã thật.

## Bằng chứng

- `ui/src/pages/Audit/components/AuditActionBadge.tsx:12-84` (khoá `ai:…`) và `:86-127` (khớp theo chuỗi con).
- `app/infra/database/console_store.py:246,260,308`; `app/infra/database/console_vision_store.py:509,541,771,792`; `app/core/console/services/tools_service.py:119`.

## Sửa / kiểm chứng

Đã sửa trên nhánh `bugfix/bug-019-2026-10-audit-export-and-actions` (2026-10-24):

- `ui/src/pages/Audit/auditActionCodes.json`: danh sách chuẩn 25 mã server ghi (phần trước `:`) kèm nhóm `rbac` / `ml` / `auth` / `review`. Bỏ khoá `ai:…` cũ.
- `ui/src/pages/Audit/components/AuditActionBadge.tsx:54-70`: `getActionMeta` khớp theo tiền tố trước `:`, giữ phần sau làm chi tiết (vd `Cấp vai trò · ai_annotator`); `actionLabel` lấy nhãn từ i18n, mã lạ hiện nguyên mã. Badge dùng `useI18n` nên đổi EN thì nhãn đổi theo.
- Nhãn VI/EN: `ui/src/i18n/vi.ts:574`, `ui/src/i18n/en.ts:596` (`audit.actions`).
- Bộ lọc thêm nhóm "Chấm & gán nhãn" (`review`) cho `vision.label`, `vision.review`, `copilot.review`: `ui/src/pages/Audit/AuditPage.tsx:199`. `snapshot.*`, `model.*`, `eval.start`, `policy.*`, `knowledge.ingest_draft`, `vision.demo_seed` vào nhóm MLOps; `system.bootstrap_admin` vào nhóm phân quyền.
- Tìm kiếm theo nhãn đang hiện thay cho `labelVi` cố định: `AuditPage.tsx:85`.

Kiểm chứng:

- `test/test_console_audit_codes.py`: quét literal trong `_audit(...)`/`add_audit(...)` ở `console_store.py`, `console_vision_store.py`, `app/core/console/services/*.py`, so với file JSON; mã thêm ở server mà quên khai thì đỏ (đã thử bỏ `snapshot.freeze` khỏi danh sách → test báo thiếu đúng mã đó). PASS 3/3.
- `ui/src/pages/Audit/components/AuditActionBadge.test.tsx`: mọi mã có nhóm khác `other` và có nhãn ở cả VI lẫn EN; khớp tiền tố; `snapshot.freeze`/`snapshot.create:golden` vào MLOps; mã lạ hiện nguyên mã.
- `pnpm typecheck` PASS; `npx vitest run --maxWorkers=1` PASS 14 file / 56 test.
- Chưa xem lại trên browser (lượt kiểm browser chung làm ở cuối).
