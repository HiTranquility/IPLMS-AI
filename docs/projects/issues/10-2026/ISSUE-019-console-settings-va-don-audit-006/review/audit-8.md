# 🔎 audit-8: Convention audit — ISSUE-019 chặng 6 (sửa 4 điểm a11y từ REA)

> Mẫu của [convention audit](../../../../../../../skills/iplms-code-review/references/convention-audit.md) (IPLMS ADR-0052). Auditor viết; fixer chỉ sửa cột "Đã sửa" và trạng thái `Fixed`; auditor đặt `Verified`/`Reopened` và Kết luận.
> Báo cáo rà UI của chặng này: [review-2](review-2.md) (BUG-07…BUG-10). Audit trước: [audit-7](audit-7.md) (chặng 5). Hồ sơ: [ISSUE-019](../issue.md).

| | |
|---|---|
| **Kết luận** | ✅ Đạt (2026-10-26, vòng 1): không có P0–P2. Còn 4 P3 Open (A-76…A-79), không chặn. |
| **Vòng** | 1/3 (chặng 6 đếm vòng riêng) |
| **Phạm vi** | `ai/`, worktree `ai/.worktrees/feature/ISSUE-019-merge-develop`, **phần đã stage** (`GIT_DIR=.git/modules/ai/worktrees/ISSUE-019-merge-develop`, `git diff --cached`): 12 file, +62/−27. Code: `ui/src/components/layout/AppShell.tsx`, `ui/src/i18n/vi.ts`, `ui/src/i18n/en.ts`, `ui/src/pages/Audit/AuditPage.tsx`, `ui/src/pages/Members/MembersPage.tsx`, `ui/src/pages/Overview/OverviewPage.tsx`, `ui/src/pages/Settings/SettingsPage.tsx`, `ui/src/pages/Tools/components/ForecastSimulator/ForecastSimulator.tsx`, `ui/src/pages/Vision/components/LabelForm.tsx`, `ui/src/pages/Vision/components/LabelStudio/LabelWorkspace.tsx`. Tài liệu: `issue.md`, `review/review-2.md`. Bỏ qua mọi file chưa stage. |
| **Auditor** | Claude Code, subagent auditor độc lập, 2026-10-26. Không viết code chặng này. |
| **Fixer** | Claude Code (phiên điều phối) |
| **Máy quét** | `python -X utf8 script/audit/check_diff.py --staged --repo ai` (chạy từ gốc IPLMS, có `GIT_DIR`/`GIT_WORK_TREE` của worktree): 10 file code, **0 FAIL, 0 WARN**. |
| **Quy ước đã nạp** | `ai/ui/DESIGN.md` mục "Ngôn ngữ — VI/EN" (khoá ở `vi.ts`, `en: Messages` để tsc bắt thiếu khoá) và "Luật Hallmark" · IPLMS ADR-0041 (cổng L4 a11y + VI/EN) · WAI-ARIA APG mẫu Tabs (tablist/tab/tabpanel, `aria-controls`, `aria-labelledby`, roving `tabIndex`, ←/→; Home/End là tuỳ chọn) · WAI-ARIA 1.2 `aria-keyshortcuts`, landmark `complementary` có tên khi có nhiều hơn một · WCAG 2.5.3 Label in Name · CLAUDE.md "Surgical Changes" · AGENTS.md "Báo cáo thành file" · convention-audit §3 |

## Kết quả chạy kiểm

| Lớp | Lệnh | Kết quả |
|---|---|---|
| Máy quét | `check_diff.py --staged --repo ai` | 0 FAIL, 0 WARN |
| Typecheck UI | `npx tsc --noEmit` (worktree `ui/`) | PASS, auditor tự chạy (exit 0). Khoá mới `shell.railLabel`, `members.sideLabel` có ở cả `vi.ts:70`/`:1026` và `en.ts:84`/`:1047`. |
| Vitest | `npx vitest run --maxWorkers=1 --no-file-parallelism` | Auditor **không chạy lại** (ổ C: thấp). Số 94/94 lấy từ phiên điều phối. Diff không thêm hay sửa test nào. |
| Browser / REA | — | NOT RUN bởi auditor (không bật Chromium). Gap: chưa có lượt đo sau khi sửa để xác nhận cây a11y mới (tên bảng, landmark, tabpanel, tên nút không còn chữ phím). Xem A-77. |

### Đối chiếu từng BUG với code

| BUG | Chỗ sửa | Kết luận |
|---|---|---|
| BUG-07 Tabs | `SettingsPage.tsx:197-249`: `id`, `aria-controls`, `aria-selected`, `tabIndex` lăn (0 cho tab đang chọn, −1 cho tab khác), `onKeyDown` ←/→ vòng tròn qua `TABS` (`:37`), dời focus bằng `getElementById` (ba nút luôn được render nên id luôn có). Mỗi panel bọc `role="tabpanel"` + `aria-labelledby` (`:258`, `:585`, `:745`). | Đúng mẫu APG phần bắt buộc. Tab rời tablist đi thẳng vào nội dung panel, vì hai tab còn lại có `tabIndex=-1`. Còn hai điểm nhỏ: A-78, A-79. |
| BUG-08 Landmark | `AppShell.tsx:158` (`railLabel`), `MembersPage.tsx:234` (`sideLabel`) | Đạt. Hai `aside` có tên riêng, VI và EN đều có. |
| BUG-09 `<kbd>` | `LabelForm.tsx:160-168`, `LabelWorkspace.tsx:327-333`, `:407-435` | Đạt. `Button` chuyển `...rest` xuống `<button>` (`components/common/Ui/button/Button.tsx:14-22`), nên `aria-keyshortcuts` tới được DOM. Giá trị khớp handler thật: `LabelForm.tsx:50-52` (1/2/3), `LabelWorkspace.tsx:120-131` (1/2/3, `s`/`S`). WCAG 2.5.3: tên mới là "Đúng 100%", "Sửa", "Hỏng", "Bỏ qua mẫu này", vẫn bắt đầu bằng đúng chữ đang hiển thị. Chữ phím chỉ là gợi ý, không phải một phần của nhãn. Khi `loading`, `Button` vẫn giữ `children`, nên tên không đổi. `title` lúc này thành mô tả, không chen vào tên. |
| BUG-10 Tên bảng | `OverviewPage.tsx:99`, `MembersPage.tsx:147`, `AuditPage.tsx:227`, `SettingsPage.tsx:764`, `:837`, `ForecastSimulator.tsx:703` | Đạt. Mọi khoá đều có sẵn (tsc PASS). Ba bảng trùng tên với `section` bao ngoài (`OverviewPage.tsx:90`, `MembersPage.tsx:108`, `AuditPage.tsx:139`). Chỉ là đọc lặp, không có luật nào cấm. |

## Findings

| # | Mức | Loại | `file:line` | Luật bị vi phạm | Mô tả | Cách sửa đề xuất | Trạng thái | Đã sửa |
|---|---|---|---|---|---|---|---|---|
| A-76 | P3 | tài-liệu | `review/review-2.md:5` | AGENTS.md "Báo cáo thành file" (kết quả một dòng phải đúng) | Câu kết quả một dòng đã thêm "REA chạy sau thêm 4 điểm a11y", nhưng cuối câu vẫn ghi "**REA: BLOCKED** vì ổ C: chỉ còn dưới 3 GB". Câu này trái với hàng REA ở `:76`, nơi ghi đã chạy lại khi ổ còn 12 GB. | Bỏ "REA: BLOCKED…" hoặc đổi thành "REA: lượt đầu BLOCKED, chạy lại PASS sau khi dọn đĩa". | Open | — |
| A-77 | P3 | test | `ui/src/pages/Settings/SettingsPage.tsx:200-208`; `review/review-2.md:43-46`, `:76` | Quality gate L4 (a11y có số đo); convention-audit §3.4 | Không có test nào giữ hành vi mới: ←/→ đổi tab và dời focus, `tabpanel`, `kbd` bị `aria-hidden`. Hàng REA ở review-2 chỉ ghi "đã sửa", chưa có lượt đo sau sửa. Bảng BUG-07…10 ghi tên file, không có số dòng. | Thêm một test Testing Library cho `SettingsPage` (focus tab, `ArrowRight`, kiểm `aria-selected` và `document.activeElement`), có thể cả `getByRole('button', { name: 'Đúng 100%' })`. Chạy lại REA hoặc script đo trên các màn đã sửa và ghi số đo sau sửa vào review-2. | Open | — |
| A-78 | P3 | đúng-sai | `ui/src/pages/Settings/SettingsPage.tsx:214`, `:227`, `:257` | WAI-ARIA 1.2 `aria-controls` (IDREF phải trỏ tới phần tử có trong DOM) | Panel `compute`/`policy` chỉ render khi `data` có (`:257`, `:584`). Lúc đang tải hoặc lỗi, tab đang chọn trỏ `aria-controls` tới id không tồn tại. Tab không được chọn cũng luôn trỏ tới panel chưa render. Trường hợp sau phổ biến và được chấp nhận; trường hợp trước có thể bị axe báo `aria-valid-attr-value`. | Luôn render khung `div role="tabpanel"` của tab đang chọn, đặt `Loading`/`ErrorBlock` bên trong; điều kiện `data` chỉ bọc nội dung. | Open | — |
| A-79 | P3 | quy-ước | `ui/src/pages/Settings/SettingsPage.tsx:198-200`, `:258`, `:585`, `:745` | WAI-ARIA APG Tabs (khuyến nghị, không bắt buộc) | (a) `tablist` chưa có tên (`aria-label`/`aria-labelledby`). (b) Panel không có `tabIndex={0}`, trong khi phần tử đầu của panel là `section`/`h2`, không nhận focus. APG khuyên đặt `tabIndex=0` trong trường hợp này. (c) Panel `policy` (`:585-739`) bọc thêm `div` nhưng phần bên trong không thụt lề lại, lệch với hai panel còn lại. Không có formatter nào bắt lỗi này. | Thêm `aria-label={s.title}` (hoặc khoá mới VI+EN) cho tablist và `tabIndex={0}` cho ba panel. Thụt lề panel `policy` khi có dịp. Không chặn. | Open | — |

Trạng thái: `Open` → `Fixed` (fixer) → `Verified` (auditor) · `Reopened` · `Deferred` (P3, kèm hồ sơ theo dõi).
Loại: `quy-ước` · `hợp-đồng` · `đúng-sai` · `test` · `bảo-mật` · `hiệu-năng` · `tài-liệu`.

### Theo loại (Open + Reopened)

| Loại | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| tài-liệu | 0 | 0 | 0 | 1 (A-76) |
| test | 0 | 0 | 0 | 1 (A-77) |
| đúng-sai | 0 | 0 | 0 | 1 (A-78) |
| quy-ước | 0 | 0 | 0 | 1 (A-79) |
| **Tổng** | **0** | **0** | **0** | **4** |

## WARN đã xét

Không có WARN.

## Bug đã mở

Không mở. A-78 là lệch thuộc tính ARIA chỉ xảy ra lúc tải hoặc lỗi. Nó không làm sai hành vi, dữ liệu hay quyền, nên không cần hồ sơ `bug-NNN`.

## Ngoài phạm vi (nợ cũ nhìn thấy)

- `ui/src/pages/Tools/components/ForecastSimulator/ForecastSimulator.tsx:702-707`: bảng ma trận đặc trưng vẫn dùng inline style và px cứng (`padding: '6px'`), có từ trước. Đã ghi ở audit-7, không tính lại.
- `issue.md` mục tiêu chí chấp nhận, dòng `tsc`/vitest "93/93" (dòng ngữ cảnh, không đổi trong diff) đã cũ so với 94/94.

## Soát lại

Mỗi vòng (lượt auditor) một dòng; tối đa 3 vòng, vòng 2–3 chỉ soát delta của fixer + finding `Fixed`. `Tree` = `git write-tree` của index lúc bắt đầu vòng.

| Lần | Ngày | Tree | Finding đã soát | Kết quả |
|---|---|---|---|---|
| 1 | 2026-10-26 | `61be21b72b535c24044f85e3e8406128388b158a` | Toàn bộ phần đã stage của chặng 6 (12 file) | 0 P0–P2. Mở A-76…A-79 (P3). Máy quét: 0 FAIL, 0 WARN. tsc PASS (auditor chạy). Vitest không chạy lại. |
