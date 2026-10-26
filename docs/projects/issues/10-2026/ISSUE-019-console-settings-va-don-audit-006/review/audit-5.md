# 🔎 audit-5: Convention audit — ISSUE-019 chặng 3 (sửa UI sau review-1)

> Mẫu của [convention audit](../../../../../../../skills/iplms-code-review/references/convention-audit.md) (IPLMS ADR-0052). Auditor viết; fixer chỉ sửa cột "Đã sửa" và trạng thái `Fixed`; auditor đặt `Verified`/`Reopened` và Kết luận.
> Vòng trước của chặng 2: [audit-4](audit-4.md). Báo cáo rà UI của chặng này: [review-1](review-1.md). Hồ sơ: [ISSUE-019](../issue.md).

> **Ghi chú sự cố (2026-10-26).** Lúc ghi vòng 2, ổ C: hết dung lượng (`ENOSPC`, 0 byte trống; nguyên nhân là Chrome headless của phiên điều phối, đã tắt). Lệnh ghi đã cắt file về 0 byte nên mất bản vòng 1 và mục "Đã sửa" của fixer. File này được **dựng lại** sau khi giải phóng ổ: mô tả finding vòng 1 viết lại từ code hiện tại và review-1, không phải nguyên văn. Cột "Đã sửa" chép theo lời fixer, kèm `file:line` auditor đối chiếu. **Fixer cần kiểm lại cột "Đã sửa".** Kết quả vòng 2 không đổi so với bản đã soạn trước sự cố.

| | |
|---|---|
| **Kết luận** | ✅ Đạt sau soát lại (2026-10-26, vòng 2): không còn P0–P2 Open/Reopened. A-67 (P3) còn Open, không chặn. |
| **Vòng** | 2/3 (chặng 3 đếm vòng riêng) |
| **Phạm vi** | `ai/`, nhánh `feature/ISSUE-019-2026-10-console-settings-audit-006`, working tree chưa stage (`git diff HEAD`). Phần chặng 3 là các file UI theo review-1: `ui/src/pages/Settings/SettingsPage.tsx`, `SettingsPage.module.css`, `ui/src/pages/Vision/components/ReviewRow.tsx`, `ui/src/pages/Vision/CrossRoleDemoLoop.test.tsx`, `ui/src/pages/Vision/ReviewRowNames.test.tsx` (mới), `ui/src/pages/Tools/components/ForecastSimulator/*`, `ui/src/pages/Overview/**`, `ui/src/i18n/vi.ts`, `ui/src/i18n/en.ts`. |
| **Auditor** | Claude Code, subagent auditor độc lập, 2026-10-26. Không viết code chặng này. |
| **Fixer** | Claude Code (phiên điều phối) |
| **Máy quét** | `python -X utf8 script/audit/check_diff.py --root ai`: vòng 2 có 105 file, **0 FAIL, 0 WARN**. Chạy lại sau khi A-69 được sửa: 105 file, 0 FAIL, 0 WARN. |
| **Quy ước đã nạp** | `ai/ui/DESIGN.md` (i18n VI/EN, a11y, bố cục responsive) · `ai/docs/standards/AI_CONVENTIONS.md` mục Kiểm chứng · IPLMS ADR-0041 (cổng L1–L8: a11y + VI/EN, viewport) · WCAG 2.5.3 Label in Name · convention-audit §3.4 (assertion phải chứng minh đúng điều cần chứng minh) |

## Kết quả chạy kiểm

| Lớp | Lệnh | Kết quả |
|---|---|---|
| Máy quét | `check_diff.py --root ai` | 0 FAIL, 0 WARN (vòng 2 và lần chạy lại sau A-69) |
| Typecheck UI | `npx tsc --noEmit` (ai/ui) | PASS ở vòng 2. Sau sửa A-69, fixer báo tsc PASS; auditor chỉ đọc dòng sửa. |
| Vitest | — | NOT RUN bởi auditor. Fixer báo 94/94. |
| Browser | — | NOT RUN. A-66 (1440/1920px), A-67 và A-69 kết luận từ đọc code. Gap: chưa đo lại trên browser. |

## Findings

| # | Mức | Loại | `file:line` | Luật bị vi phạm | Mô tả | Cách sửa đề xuất | Trạng thái | Đã sửa |
|---|---|---|---|---|---|---|---|---|
| A-62 | P2 | đúng-sai | `ui/src/pages/Settings/SettingsPage.tsx:364`, `:381`, `:398`, `:553` | DESIGN (không báo sai trạng thái) | Loading của nút preset dựa vào state `pendingPreset` riêng, không gắn với mutation, nên có thể lệch trạng thái thật. Nút Lưu của form compute cũng quay khi đang áp preset. | Lấy trạng thái từ `updateCompute.variables?.preset`; nút Lưu chỉ quay khi `!variables?.preset`. | Verified (vòng 2) | Bỏ `pendingPreset`; `loading` theo `updateCompute.variables?.preset` (`:364`, `:381`, `:398`); nút Lưu `:553` |
| A-63 | P3 | đúng-sai | `ui/src/pages/Settings/SettingsPage.tsx:365`, `:382`, `:399`, `:553` | — (gợi ý) | Trong lúc đang ghi, các nút preset khác và nút Lưu vẫn bấm được, có thể gửi chồng request. | `disabled={updateCompute.isPending}` cho cả 4 nút. | Verified (vòng 2) | `:365`, `:382`, `:399`, `:553` |
| A-64 | P2 | đúng-sai | `ui/src/pages/Vision/components/ReviewRow.tsx:21-24`, `:162`, `:171` | WCAG 4.1.2 / cổng L4 a11y (review-1 BUG-05) | Nhãn UNUSABLE không có biển đề xuất thì tên nút Duyệt/Trả lại bị trùng giữa các dòng (không phân biệt được bằng screen reader). | `rowPlate()` lấy biển đề xuất, không có thì `machine_plate`, rồi `capture_id`; thêm test. | Verified (vòng 2) | `rowPlate()` `:21-24`; test `ui/src/pages/Vision/ReviewRowNames.test.tsx` |
| A-65 | P3 | quy-ước | `ui/src/i18n/vi.ts:914-915`, `:1191-1192`; `ui/src/i18n/en.ts:935-936`, `:1212-1213` | `ai/ui/DESIGN.md` i18n (không hardcode chuỗi hiển thị) | Tên accessible của nút được ghép chuỗi trực tiếp trong component. | Chuyển sang hàm từ điển (`approveFor`, `rejectFor`, `applyPresetFor`, `activePresetFor`) ở cả VI và EN. | Verified (vòng 2) | Các khoá trên có ở cả hai file |
| A-66 | P3 | quy-ước | `ui/src/pages/Tools/components/ForecastSimulator/ForecastSimulator.tsx:674` | DESIGN bố cục responsive | Hàng 7 ngày dùng `auto-fill`, ở màn rộng để lại cột trống. | Dùng `auto-fit`. | Verified (vòng 2, đọc code; chưa đo 1440/1920) | `repeat(auto-fit, minmax(4.5rem, 1fr))` `:674` |
| A-67 | P3 | quy-ước | `ui/src/pages/Overview/OverviewPage.tsx:92`; `components/TrendChart.tsx:88`; `components/DistributionSection.tsx:34`, `:95`, `:149` | WCAG 1.3.1 (thứ bậc heading) | Thứ bậc heading trang Tổng quan chưa đều sau khi sửa BUG-04 của review-1 (h2/h3 giữa các khối). Chi tiết nguyên văn vòng 1 đã mất trong sự cố, xem ghi chú đầu file. | Xếp lại để mỗi h3 nằm dưới một h2 của khối chứa nó. | Open (fixer để lại, không chặn) | — |
| A-68 | P3 | test | `ui/src/pages/Vision/CrossRoleDemoLoop.test.tsx:121`, `:127` | convention-audit §3.4 | Test tìm nút theo tên một phần, nên vẫn pass khi tên các dòng bị trùng. | Kiểm đúng tên đầy đủ. | Verified (vòng 2) | `getByRole('button', { name: 'Duyệt nhãn 51A-123.45' })` |
| A-69 | P3 | quy-ước | `ui/src/i18n/en.ts:936` | WCAG 2.5.3 Label in Name | Bản EN hiện chữ "Send back…" (`rejectOpen`, `:948`) nhưng tên accessible là "Return label X", không chứa chữ đang hiển thị. Người dùng điều khiển bằng giọng nói sẽ không gọi được nút. (Mở ở vòng 2.) | `rejectFor` thành `` `Send back label ${plate}` ``. | Verified (vòng 2, sau khi fixer sửa) | `en.ts:936` `` rejectFor: (plate) => `Send back label ${plate}` `` |

Trạng thái: `Open` → `Fixed` (fixer) → `Verified` (auditor) · `Reopened` · `Deferred` (P3, kèm hồ sơ theo dõi).
Loại: `quy-ước` · `hợp-đồng` · `đúng-sai` · `test` · `bảo-mật` · `hiệu-năng` · `tài-liệu`.

Ghi nhận cho A-69: bản VI hiện "Áp dụng cấu hình này", còn tên accessible là "Áp dụng cấu hình <tên preset>" (`vi.ts:1190-1191`). Hai chuỗi lệch nhẹ nhưng tên vẫn bắt đầu bằng phần chữ đang hiển thị, nên không mở finding.

### Theo loại (Open + Reopened)

| Loại | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| quy-ước | 0 | 0 | 0 | 1 (A-67) |
| **Tổng** | **0** | **0** | **0** | **1** |

## WARN đã xét

Không có WARN (0 WARN ở cả hai lần chạy).

## Bug đã mở

Không có.

## Ngoài phạm vi (nợ cũ nhìn thấy)

Không ghi thêm. Nợ cũ của chặng 2 nằm ở [audit-4](audit-4.md).

## Soát lại

Mỗi vòng (lượt auditor) một dòng; tối đa 3 vòng, vòng 2–3 chỉ soát delta của fixer + finding `Fixed`. `Tree` = `git write-tree` của index lúc bắt đầu vòng.

| Lần | Ngày | Tree | Finding đã soát | Kết quả |
|---|---|---|---|---|
| 1 | 2026-10-26 | (mất trong sự cố ENOSPC) | Toàn diff chặng 3 | Mở A-62…A-68 (2 P2, 5 P3) |
| 2 | 2026-10-26 | `3c80d1517e45cf83f65646c80857e380f68d698c` (chưa stage gì) | A-62…A-66, A-68 | Verified 6. A-67 còn Open. Mở A-69 (P3). Sau đó fixer sửa A-69 ngay trong lượt (chưa stage, tree không đổi), auditor đối chiếu `en.ts:936` và đặt Verified. Máy quét chạy lại: 0 FAIL, 0 WARN. |
