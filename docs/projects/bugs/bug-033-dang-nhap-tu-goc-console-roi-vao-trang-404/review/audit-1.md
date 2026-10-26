# 🔎 audit-1: Convention audit — bug-033 lưu trang quay lại theo đường dẫn router

> Mẫu của [convention audit](../../../../../../../skills/iplms-code-review/references/convention-audit.md) (IPLMS ADR-0052). Auditor viết; fixer chỉ sửa cột "Đã sửa" và trạng thái `Fixed`; auditor đặt `Verified`/`Reopened` và Kết luận.
> Hồ sơ: `bug.md` của bug-033 hiện nằm ở nhánh `docs/ISSUE-020-2026-10-ai-console-demo-audit-plan`, chưa có trên nhánh này. Vì vậy hồ sơ được nêu bằng tên, không dùng link (link sẽ gãy cho tới khi hai nhánh gộp).

| | |
|---|---|
| **Kết luận** | ✅ Đạt (2026-10-26, vòng 1): không có finding P0–P2. Có 1 gợi ý P3 (A-1) đang Open, không chặn commit. |
| **Vòng** | 1/3 |
| **Phạm vi** | `ai/`, nhánh `bugfix/bug-033-2026-10-dang-nhap-tu-goc-console-404` (tách từ `origin/develop` `bdeba06`), **phần đã stage**: 2 file. `ui/src/pages/Auth/LoginPage.tsx` có 2 hunk (+5/−2). `ui/src/pages/Auth/LoginPage.test.tsx` là file mới, 33 dòng. |
| **Auditor** | Claude Code, subagent auditor độc lập, 2026-10-26. Không viết code chặng này. |
| **Fixer** | Claude Code (phiên điều phối bug-033) |
| **Máy quét** | `check_diff.py --root .worktrees/bugfix/bug-033-… --staged --repo ai` (chạy từ gốc IPLMS, đặt `GIT_DIR`/`GIT_WORK_TREE` của worktree submodule): 2 file code, **0 FAIL, 0 WARN** |
| **Quy ước đã nạp** | `ai/ui/DESIGN.md` (mục đầu: app độc lập, phiên cookie; mục "Cấu trúc" `test/`) · `ai/docs/standards/AI_CONVENTIONS.md` (không có mục riêng cho UI/vitest) · quy ước test của `ui/src`: `src/App.test.tsx`, `src/test/utils.tsx` (`mockApi`/`renderWithProviders` + `MemoryRouter`), `src/test/setup.ts` (`vi.restoreAllMocks` sau mỗi ca) · CLAUDE.md "Surgical Changes", "Simplicity First" · convention-audit §3 |

## Kết quả chạy kiểm

| Lớp | Lệnh | Kết quả |
|---|---|---|
| Máy quét | `check_diff.py --staged --repo ai` | 0 FAIL, 0 WARN |
| Vitest (auditor tự chạy) | `npx vitest run src/pages/Auth/LoginPage.test.tsx src/App.test.tsx` trong `ui/` của worktree | 8/8 pass |
| Test đỏ trước khi sửa | Auditor không chạy (không được sửa code để quay lại bản cũ). Đã suy từ code: bản cũ đọc `window.location.pathname`, mà test đặt nó bằng `replaceState` thành `/console/` và `/console/settings?tab=sessions`. Ca 1 khi đó lưu `/console/`, khác `null`. Ca 2 lưu `/console/settings?tab=sessions`, khác giá trị mong đợi. Cả hai ca đều đỏ đúng triệu chứng, khớp lời fixer. | Suy từ code |
| tsc, toàn bộ vitest, `vite build`, browser qua `vite preview` | — | NOT RUN bởi auditor. Kết quả "tsc exit 0, 22 file/99 test, build OK, đăng nhập từ `/console/` vào `/console/members`" là lời báo của fixer, auditor chưa tự tái hiện. Lớp runtime (L3 browser) vẫn là gap của auditor. |

### Hợp đồng hai đầu: khoá `console_return_to` trong sessionStorage

| Đầu ghi (diff) | Đầu đọc | Kết luận |
|---|---|---|
| `LoginPage.tsx:50-52` lưu `location.pathname + location.search` của router. Giá trị này đã bỏ basename `/console`. Khi `location.pathname === '/'` thì không lưu. | `routes/AuthenticatedRoutes.tsx:24-28`: `Home` đọc khoá, xoá ngay, rồi `<Navigate to={returnTo} replace>` khi giá trị bắt đầu bằng `/`, không bắt đầu bằng `//` và không bắt đầu bằng `/auth`. `<Navigate>` nằm trong `BrowserRouter basename={basename}` (`main.tsx:14`, `:21`), nên tự cộng basename. | Khớp. Đường dẫn tương đối với router đúng ở cả hai gốc. Ở `/`, `basename` là `undefined`. Ở `/console`, `basename` là `/console`. Trường hợp chéo cũng đúng: lưu khi đứng ở `/`, sau đó callback Google đưa về `/console/…`. Bản cũ chỉ đúng khi không có basename. |
| Nút Google `onClick={saveReturnTo}` (`LoginPage.tsx`, khối `<a href={AUTH_ENDPOINTS.GOOGLE_START}>`) | Cùng `Home` sau khi callback quay về | Dùng chung hàm đã sửa. Không cần sửa thêm. |
| `useLocation()` (`LoginPage.tsx:44`) cần nằm trong Router | Có hai nơi render `LoginPage`. `AuthenticatedGuard.tsx:21` nằm trong `App`, `App` nằm trong `BrowserRouter` (`main.tsx:21-23`). `AnonymousRoutes.tsx:9` nằm trong `<Routes>`. Trong test, `renderWithProviders` bọc `MemoryRouter`. | An toàn. Không có chỗ nào render `LoginPage` ngoài Router. |

Tiêu chí của bug-033 ("Hành vi mong đợi": xác thực xong vào trang đầu hợp với vai, URL không lặp `/console`; "Sửa / kiểm chứng": thêm vitest cho `saveReturnTo` với basename). Đọc code thì thấy đã phủ. Gốc `/console/` → không lưu → `Home` chọn trang theo vai. Trang con → lưu đường dẫn router → không lặp tiền tố. Phần browser chỉ có bằng chứng của fixer.

Soát theo §3. Diff không thêm package. Diff không đổi format hay comment lân cận. Comment mới ở `:50` giải thích lý do và trỏ về bug-033, không thừa. `callbackError` và `return_to` vẫn đọc `window.location.search`. Chỗ này không sai vì phần query giống nhau dù có basename hay không, và diff không đổi nó (Surgical Changes). Test dùng helper chung `mockApi`/`renderWithProviders`/`ok`/`fail`, nhãn tiếng Việt và tên ca mô tả hành vi, giống `App.test.tsx`. `afterEach` dọn `sessionStorage` và `history`. `fetch` đã được `setup.ts:7` khôi phục. Test không có `.only`/`.skip`. Assertion so giá trị chính xác (`toBeNull`, `toBe('/settings?tab=sessions')`), không khớp tiền tố.

## Findings

| # | Mức | Loại | `file:line` | Luật bị vi phạm | Mô tả | Cách sửa đề xuất | Trạng thái | Đã sửa |
|---|---|---|---|---|---|---|---|---|
| A-1 | P3 | test | `ui/src/pages/Auth/LoginPage.test.tsx:7-10` | convention-audit §3.4 (test chứng minh đúng điều cần chứng minh). bug-033 mục "Sửa / kiểm chứng" ("vitest cho `saveReturnTo` với basename") | Test tự cắt basename: truyền `routerPath` riêng vào `MemoryRouter`. Nó chứng minh `LoginPage` đọc vị trí của router chứ không đọc `window`, nhưng không chạy `basename` thật. Nó cũng không chạy đầu đọc (`Home` → `<Navigate>`), là chỗ sinh `/console/console/`. Một lần đổi sau này ở `Home` (ví dụ ghép thêm basename) hoặc ở `main.tsx` vẫn sẽ qua test này. Hiện chỉ browser check của fixer phủ được cả vòng. | Tuỳ chọn. Thêm một ca render `<BrowserRouter basename="/console">` sau `replaceState('/console/')`, hoặc thêm một ca cho `Home`: đặt `console_return_to='/settings'` rồi kiểm `window.location.pathname === '/console/settings'`. Không chặn commit. Có thể `Deferred` kèm lý do "browser check đã phủ". | Deferred | Browser thật đã phủ basename `/console`: `vite preview` :5191 → đăng nhập admin từ `/console/` vào `/console/members` (2026-10-26). Ca BrowserRouter basename để vòng sau nếu đổi luồng return_to. |

Trạng thái: `Open` → `Fixed` (fixer) → `Verified` (auditor) · `Reopened` · `Deferred` (P3, kèm hồ sơ theo dõi).

### Theo loại

| Loại | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| test | 0 | 0 | 0 | 1 |

## WARN đã xét

Không có WARN.

## Bug đã mở

Không có. Bản sửa đúng hành vi, không phát hiện lỗi chạy sai mới. Đã xem `docs/projects/bugs/`: bug-033 là hồ sơ đang xử lý, không có hồ sơ trùng.

## Ngoài phạm vi (nợ cũ nhìn thấy)

- `ui/src/pages/Auth/LoginPage.tsx:48-49`: tham số `return_to` lấy thẳng từ query và lưu nguyên văn. Nếu ai đó truyền `return_to=/console/x`, giá trị vẫn bị lặp tiền tố. Trong repo chưa có nơi nào sinh `return_to` (đã grep `ui/src` và `app/`), nên hiện không gây lỗi. Đây là nợ cũ, không phải do diff này.
- Hồ sơ `bug.md` của bug-033 nằm ở nhánh `docs/ISSUE-020-…`. Mục "Sửa / kiểm chứng" và Trạng thái `🆕 New` cần cập nhật khi hai nhánh gặp nhau. Đây là việc của người điều phối, không phải finding code.

## Soát lại

Mỗi vòng (lượt auditor) một dòng; tối đa 3 vòng, vòng 2–3 chỉ soát delta của fixer + finding `Fixed`. `Tree` = `git write-tree` của index lúc bắt đầu vòng.

| Lần | Ngày | Tree | Finding đã soát | Kết quả |
|---|---|---|---|---|
| 1 | 2026-10-26 | `f122f75f4362499b20e9a8d9670f92c6dd256761` | Audit đầu: 2 file stage | A-1 P3 Open. Không có P0–P2. |
