# 🔎 audit-7: Convention audit — ISSUE-019 chặng 5 (sửa UI sau review-2)

> Mẫu của [convention audit](../../../../../../../skills/iplms-code-review/references/convention-audit.md) (IPLMS ADR-0052). Auditor viết; fixer chỉ sửa cột "Đã sửa" và trạng thái `Fixed`; auditor đặt `Verified`/`Reopened` và Kết luận.
> Báo cáo rà UI của chặng này: [review-2](review-2.md). Vòng trước của chặng 4: [audit-6](audit-6.md). Hồ sơ: [ISSUE-019](../issue.md).

| | |
|---|---|
| **Kết luận** | ✅ Đạt (2026-10-26, vòng 1): không có P0–P2. Còn 2 P3 Open (A-74, A-75), không chặn. |
| **Vòng** | 1/3 (chặng 5 đếm vòng riêng) |
| **Phạm vi** | `ai/`, nhánh `feature/ISSUE-019-2026-10-console-settings-audit-006`, **phần đã stage** (`git -C ai diff --cached`): 15 file, +93/−22. Code: `ui/src/i18n/vi.ts`, `ui/src/i18n/en.ts`, `ui/src/pages/Audit/components/AuditActionBadge.module.css`, `ui/src/pages/Settings/SettingsPage.tsx`, `ui/src/pages/Tools/ToolsPage.module.css`, `ui/src/pages/Tools/components/ForecastSimulator/ForecastSimulator.module.css`, `ForecastSimulator.tsx`, `ui/src/pages/Tools/components/IngestSection.tsx`, `ui/src/pages/Vision/ReviewPage.tsx`, `ui/src/pages/Vision/components/LabelStudio/LabelStudio.module.css`. Tài liệu: `review/review-2.md` và 4 ảnh `evidence/review-2-*.jpg`. Bỏ qua mọi file chưa stage. |
| **Auditor** | Claude Code, subagent auditor độc lập, 2026-10-26. Không viết code chặng này. |
| **Fixer** | Claude Code (phiên điều phối) |
| **Máy quét** | `python -X utf8 script/audit/check_diff.py --staged --repo ai` (chạy từ gốc IPLMS): 10 file code, **0 FAIL, 0 WARN**. |
| **Quy ước đã nạp** | `ai/ui/DESIGN.md` mục "Thị giác — Graphite & Amber" (bảng token), "Ngôn ngữ — VI/EN", "Luật Hallmark" luật 8 (màu chỉ qua token, ngoại lệ `AuditActionBadge`/`RoleBadge`) · `ai/ui/src/index.css` (giá trị token hai theme) · IPLMS ADR-0041 (cổng L1–L8: L2 màu light/dark, L3 viewport, L4 a11y + VI/EN) · WCAG 2.5.3 Label in Name, 1.4.3 Contrast · convention-audit §3 |

## Kết quả chạy kiểm

| Lớp | Lệnh | Kết quả |
|---|---|---|
| Máy quét | `check_diff.py --staged --repo ai` | 0 FAIL, 0 WARN |
| Typecheck UI | `npx tsc --noEmit` (ai/ui) | PASS (auditor tự chạy). Khoá `revokeSessionFor` khai ở `vi.ts` và `en.ts: Messages`, nên thiếu một bên là tsc báo. |
| Vitest | `npx vitest run --maxWorkers=1 --no-file-parallelism` (ai/ui) | 94/94, 20/20 file (lần chạy thứ 3). Lần thứ 2 có 9 file lỗi ở bước nạp file, không phải ở assertion; chạy lại thì xanh hết, không có thay đổi nào ở giữa. Ghi nhận là lỗi môi trường (ổ C: gần đầy), không phải lỗi test. |
| Browser / đo tương phản | — | NOT RUN bởi auditor (không bật Chromium vì ổ C: thấp). Số đo `scrollWidth` và tỉ lệ WCAG lấy từ review-2. Auditor tự tính lại tương phản từ giá trị token trong `index.css` (xem bảng dưới). Gap: chưa đo lại bố cục 375/1024 trên browser. |

### Đối chiếu token màu mới dùng (cả hai theme, `ui/src/index.css`)

| Chỗ dùng | Token | Sáng | Tối | Tự tính |
|---|---|---|---|---|
| `ForecastSimulator.tsx:391`, `:482`; `ReviewPage.tsx:111`; `LabelStudio.module.css:597` | `--color-accent-ink` trên `--color-accent` | `:26` `#1c1204` / `#d97706` | `:61` `#1c1204` / `#f59e0b` | Khoảng 5.8:1 / 8.6:1, khớp review-2. Token có trong bảng DESIGN. |
| `LabelStudio.module.css:597` (trước khi sửa) | `--color-on-primary` | — | — | Không có trong `index.css` (grep = 0). Xác nhận đúng nguyên nhân BUG-02. |
| `ToolsPage.module.css:518` | `--color-primary-contrast` trên `--color-danger` | `:22` `#ffffff` / `#b91c1c`: 6.5:1 | `:57` `#131312` / `#f87171`: 6.7:1 | Đạt. Trước khi sửa, `#fff` trên `#f87171` ở theme tối chỉ đạt khoảng 2.8:1. Cùng cách ghép với `Button.module.css:26` (`.danger`). |
| `AuditActionBadge.module.css:27` | `#1d4ed8` cứng | Nằm trong file ngoại lệ của DESIGN luật 8. Theme tối vẫn dùng override `:global([data-theme='dark']) .info` có sẵn. | — | Đạt 4.5:1 theo review-2 (5.83:1). |

### Tên accessible (WCAG 2.5.3)

- `SettingsPage.tsx:770-774`: chữ hiển thị là `revokeSessionBtn`. VI: "Thu hồi phiên" → tên là "Thu hồi phiên #n của … (đăng nhập …)". EN: "Revoke session" → "Revoke session #n of … (signed in …)". Cả hai tên đều bắt đầu bằng đúng chữ đang hiển thị. Khi đang `loading`, `Button` vẫn giữ `children` (`components/common/Ui/button/Button.tsx:24-25`), nên tên không lệch. Giờ trong tên dùng `fmtDateTime` + `DASH` giống cột "Tạo lúc" (`:759`), nên khớp với chữ trên màn.
- `IngestSection.tsx:376`: `t.tools.category` có ở `vi.ts:539` ("Phân loại") và `en.ts:560` ("Category"), là con trực tiếp của `tools`.
- Không có chuỗi hiển thị mới viết cứng. Hai comment CSS mới là comment, không phải chuỗi hiển thị.

## Findings

| # | Mức | Loại | `file:line` | Luật bị vi phạm | Mô tả | Cách sửa đề xuất | Trạng thái | Đã sửa |
|---|---|---|---|---|---|---|---|---|
| A-74 | P3 | tài-liệu | `ui/src/pages/Tools/ToolsPage.module.css:518` | CLAUDE.md "Surgical Changes" (mỗi dòng đổi truy được về yêu cầu) · AGENTS.md "Báo cáo thành file" | Dòng `color: #fff` → `var(--color-primary-contrast)` của nút xác nhận xoá tài liệu (`IngestSection.tsx:466`) là sửa đúng: ở theme tối, tương phản tăng từ khoảng 2.8:1 lên 6.7:1. Nhưng review-2 không ghi dòng này trong bảng Bug hay ở đâu khác, nên không truy được từ báo cáo. | Thêm một dòng vào review-2 (BUG-03 hoặc một mục riêng), ghi `ToolsPage.module.css:518` và số đo trước/sau. | Open | — |
| A-75 | P3 | quy-ước | `ui/src/pages/Audit/components/AuditActionBadge.module.css:27` | `ai/ui/DESIGN.md` luật 8 (gợi ý, không vi phạm: file nằm trong danh sách ngoại lệ) | Giá trị mới `#1d4ed8` trùng hẳn với token `--color-info` của theme sáng (`index.css:35`). Viết cứng như hiện tại thì sau này đổi token sẽ phải sửa hai chỗ. | Có thể dùng `var(--color-info)`, nhưng không bắt buộc. Nếu giữ màu cứng như các mục khác trong file thì đóng finding này. | Open | — |

Trạng thái: `Open` → `Fixed` (fixer) → `Verified` (auditor) · `Reopened` · `Deferred` (P3, kèm hồ sơ theo dõi).
Loại: `quy-ước` · `hợp-đồng` · `đúng-sai` · `test` · `bảo-mật` · `hiệu-năng` · `tài-liệu`.

### Theo loại (Open + Reopened)

| Loại | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| quy-ước | 0 | 0 | 0 | 1 (A-75) |
| tài-liệu | 0 | 0 | 0 | 1 (A-74) |
| **Tổng** | **0** | **0** | **0** | **2** |

## WARN đã xét

Không có WARN.

## Bug đã mở

Auditor không mở bug nào. Quan sát về phiên "chờ MFA" bị dồn lại (review-2, phần "Ngoài `ai/ui`") đã có hồ sơ [bug-030](../../../../bugs/bug-030-phien-cho-mfa-ton-dong-trong-danh-sach/bug.md) (🆕 New). Phiên điều phối stage hồ sơ này trong lúc audit đang chạy. Lỗi thuộc `app/`, ngoài diff này, nên không mở bản trùng.

## Ngoài phạm vi (nợ cũ nhìn thấy)

- `ui/src/pages/Tools/components/ForecastSimulator/ForecastSimulator.tsx:482`: inline style vẫn có `marginBottom: '8px'` (px cứng, có từ trước, không phải dòng mới). Các dòng `:385-394` cũng dùng inline style thay vì CSS module.
- Không có test nào giữ cho BUG-02/03/04 khỏi lặp lại (dùng token không tồn tại, hoặc `#fff` trên accent). Đây chính là S2 của review-2, chưa làm.

## Soát lại

Mỗi vòng (lượt auditor) một dòng; tối đa 3 vòng, vòng 2–3 chỉ soát delta của fixer + finding `Fixed`. `Tree` = `git write-tree` của index lúc bắt đầu vòng.

| Lần | Ngày | Tree | Finding đã soát | Kết quả |
|---|---|---|---|---|
| 1 | 2026-10-26 | `e711fb57cba45156113a8997c00776e3d9ef3411` | Toàn bộ phần đã stage của chặng 5 | 0 P0–P2. Mở A-74 và A-75 (P3). Máy quét: 0 FAIL, 0 WARN. tsc PASS, vitest 94/94. Trong lúc audit, index đổi sang `690f3bb65d2bd2c7e2312034af33b39b08924f0b`: chỉ thêm `docs/projects/bugs/bug-030-…/bug.md` (+41 dòng, tài liệu, không có code). Auditor đã đọc phần đầu file, đóng dấu trên tree này. |
