# 🔎 audit-1: Convention audit — ISSUE-020 runner nhiều vai `console-roles.demo.mjs`

> Mẫu của [convention audit](../../../../../../../skills/iplms-code-review/references/convention-audit.md) (IPLMS ADR-0052). Auditor viết; fixer chỉ sửa cột "Đã sửa" và trạng thái `Fixed`; auditor đặt `Verified`/`Reopened` và Kết luận.
> Báo cáo của chặng: [review-1](review-1.md). Hồ sơ: [ISSUE-020](../issue.md).

| | |
|---|---|
| **Kết luận** | ✅ Đạt sau soát lại (2026-10-26, vòng 2): A-1…A-4 Verified, không còn finding mở. |
| **Vòng** | 2/3 |
| **Phạm vi** | `ai/`, nhánh `docs/ISSUE-020-2026-10-ai-console-demo-audit-plan`, **phần đã stage** (`git diff --cached`): 4 file, +232. Code: `ui/e2e/demos/console-roles.demo.mjs` (file mới, 90 dòng, 1 hunk). Hồ sơ (không soát code): `issue.md`, `review/review-1.md`, `bugs/bug-033-…/bug.md`. Bỏ qua mọi file chưa stage (AGENTS.md, CLAUDE.md, ISSUE-002/003… của phiên khác). |
| **Auditor** | Claude Code, subagent auditor độc lập, 2026-10-26. Không viết code chặng này. |
| **Fixer** | Claude Code (phiên điều phối) |
| **Máy quét** | `python -X utf8 script/audit/check_diff.py --staged --repo ai` (chạy từ gốc IPLMS): 1 file code, **0 FAIL, 0 WARN** (lần 1) · 1 file code, **0 FAIL, 0 WARN** (soát lại vòng 2). |
| **Quy ước đã nạp** | `ai/docs/standards/AI_CONVENTIONS.md` (§3 REST, §8 script chạy tay; không có mục riêng cho e2e/runner) · `ai/ui/DESIGN.md` mục "Cấu trúc" · runner mẫu `frontend/e2e/demos/cross-role.demo.mjs` (header, chốt host local, BLOCKED theo vai) · CLAUDE.md "STRICT PRIVACY" (không lộ secret, không gọi host ngoài) và "Simplicity First" · AGENTS.md "Quyền chủ động và điều phối" (kết quả phân biệt đã kiểm / bị chặn), mục "Submodule" (đổi cấu trúc thì cập nhật DESIGN) · `.claude/rules/supply-chain.md` (không thêm dependency) · convention-audit §3 |

## Kết quả chạy kiểm

| Lớp | Lệnh | Kết quả |
|---|---|---|
| Máy quét | `check_diff.py --staged --repo ai` | 0 FAIL, 0 WARN |
| Cú pháp | `node --check ui/e2e/demos/console-roles.demo.mjs` (Node v22.14.0) | PASS |
| Hàm `totp()` | Chép `:31-40` ra scratchpad, chạy offline với vector RFC 6238 (secret base32 `GEZDGNBVGY3TQOJQ…`) | t=59 → `287082`, t=1111111109 → `081804`: khớp RFC. Secret chữ thường → mã khác, không báo lỗi. Thiếu secret → `TypeError` (xem A-1). |
| Chạy runner thật với console | — | NOT RUN bởi auditor (không đăng nhập tài khoản, không chạm DB). Kết quả "18/18, 2 lần giống hệt" lấy từ review-1, auditor chưa tự tái hiện. |

### Hợp đồng hai đầu (đọc phía server, không suy từ tên)

| Runner | Phía server | Kết luận |
|---|---|---|
| `API = ${BASE}/console/api` (`:16`) | `app/console_main.py:75` mount `console_router` ở `/console/api` | Khớp |
| Bảng `READS` (`:19-26`), số dòng ghi chú | `console_member_controller.py:48-50` (`/members`, `ai:member:manage`), `:84-87` (`/audit`, `ai:audit:read`); `console_vision_controller.py:21` prefix `/vision`, `:223-224` status/`ai:metrics:read`, `:234-237` queue/`ai:task:label`, `:266-269` reviews/`ai:label:approve`, `:284-286` snapshots/`require_any_permission(ai:dataset:snapshot, ai:model:evaluate)` | Khớp cả path, permission và số dòng. `[need].flat().some(...)` (`:79`) đúng nghĩa "any" của `authorize_any` (`auth_service.py:185-192`). |
| Kỳ vọng 200/403 | Không quyền nào trong 6 quyền thuộc `STEP_UP_PERMISSIONS` (`access_policy.py:41-43`), nên không có 401 `STEP_UP_REQUIRED` lẫn vào; thiếu quyền → `ConsoleAccessDenied` → 403 (`console_main.py:44-46`) | Khớp |
| `X-Console-Request: 1` (`:48`) | `console_access.py:20-27` bắt header này cho POST | Khớp |
| Đọc `json.data?.[0]`, `json.code` (`:54`) | `BaseResponse` `base_response.py:13-17`; lỗi console `_error` thêm `code` ở đỉnh (`console_main.py:32-36`) | Khớp. Nhánh `json.error?.code` không bao giờ có giá trị (envelope không có `error`), vô hại. |
| `/auth/password` → `mfa_required` (`:66-67`); `/auth/totp` `code` 6 số (`:70-73`); `/me` `roles`, `permissions`, `mfa_done` (`:75-77`) | `console_auth_controller.py:22-52`, `:105-121`, `:137-149` | Khớp |
| Mã sai ở bước +5 (`:69-70`) | `totp.py:17-18` chỉ nhận lệch ±1 bước | Chắc chắn sai, đúng như comment |
| Đăng xuất rồi `/me` (`:84-85`) | `logout` thu hồi phiên + xoá cookie (`console_auth_controller.py:130-134`, `console_access.py:59-61`) → `/me` 401 | Khớp |

Bảo mật: chốt host local ở `:15` giống runner mẫu (`cross-role.demo.mjs:18-21`); không in email, mật khẩu, secret, cookie; chỉ in tên vai lấy từ tên biến env. Không import package ngoài (`node:crypto` + `fetch` có sẵn), không đổi manifest. `vitest` mặc định chỉ nhận `*.test|spec.*`, nên `.demo.mjs` không lọt vào `pnpm test`.

## Findings

| # | Mức | Loại | `file:line` | Luật bị vi phạm | Mô tả | Cách sửa đề xuất | Trạng thái | Đã sửa |
|---|---|---|---|---|---|---|---|---|
| A-1 | P2 | đúng-sai | `ui/e2e/demos/console-roles.demo.mjs:33`, `:61-72`, `:90` | AGENTS.md "Quyền chủ động và điều phối" (kết quả phải phân biệt đã kiểm chứng với bị chặn); mẫu runner gốc `frontend/e2e/demos/cross-role.demo.mjs:37-38`, `:50`, `:103` (thiếu env hay đăng nhập lỗi thì ghi `BLOCKED` theo vai, các vai khác chạy tiếp) | Một vai có `_EMAIL` nhưng thiếu `_TOTP_SECRET` làm `totp()` ném `TypeError` (auditor đã tái hiện). Console tắt cũng làm `fetch` ném lỗi. Cả hai đều làm `Promise.all` ở `:90` reject, nên **mọi** vai mất hết dòng kết quả, chỉ còn stack trace. Secret có chữ thường, dấu cách hoặc ký tự ngoài bảng base32 thì `indexOf` trả −1 và ra mã rác, không báo lỗi. Khi đó L4 nhận 401 `TOTP_INVALID`, nhìn giống lỗi đăng nhập của app trong khi lỗi nằm ở runner/env. Thiếu `_PASSWORD` thì gửi `"undefined-sai"` rồi nhận 422, không ghi BLOCKED. | Trong `play()`: thiếu `PASSWORD`/`TOTP_SECRET` → `log('L0', 'BLOCKED: thiếu AI_QA_<ROLE>_…')` và `return out`. Chuẩn hoá secret bằng `.toUpperCase().replace(/[\s=]/g, '')`; gặp ký tự ngoài bảng base32 thì ghi BLOCKED, không tính mã. Bọc thân `play` bằng `try/catch` để lỗi mạng thành dòng `BLOCKED: <message>` của riêng vai đó (hoặc dùng `Promise.allSettled`). | Verified | `console-roles.demo.mjs`: `normalizeSecret` (hoa, bỏ khoảng/`=`, ký tự ngoài base32 → null); thiếu `PASSWORD`/secret hợp lệ → `L0 BLOCKED` và return; thân vai bọc try/catch → `L0 BLOCKED: <cause.code>`. Kiểm: thiếu secret annotator → BLOCKED, admin/reviewer chạy tiếp; secret chữ thường → 200; `AI_CONSOLE_URL=:8099` → 3 dòng `BLOCKED: ECONNREFUSED`, exit 0. |
| A-2 | P3 | test | `ui/e2e/demos/console-roles.demo.mjs:72-74` | convention-audit §3.4 (test phải chứng minh đúng điều cần chứng minh) | Server chống dùng lại mã TOTP (`console_store.py:463-472`, `totp_last_step < step`). Chạy lại runner trong cùng cửa sổ 30 giây, hoặc người dùng vừa đăng nhập UI bằng cùng tài khoản, thì L4 nhận 401 `TOTP_INVALID` và runner dừng vai đó. Kết quả này là do cách chạy, không phải lỗi app, nhưng runner không nói vậy. "2 lần chạy giống hệt" trong review-1 chỉ đúng khi hai lần cách nhau ≥ 30 giây. | Khi L4 trả `TOTP_INVALID`, đợi sang bước 30 giây kế rồi thử lại đúng một lần, hoặc in gợi ý "mã của bước này đã dùng — chạy lại sau 30 giây". Ghi lưu ý này vào header. | Verified | Header thêm lưu ý chạy lại ≥ 30 s; L4 `TOTP_INVALID` in gợi ý "mã của bước 30 s này có thể đã dùng". Kiểm: chạy hai lần liền → L4 hiện gợi ý. |
| A-3 | P3 | tài-liệu | `ui/e2e/demos/console-roles.demo.mjs:5` (và `review/review-1.md:56` "Chỉ đọc") | CLAUDE.md "Think Before Coding" (không giấu giả định) · ISSUE-020 K-scenario đọc nhật ký kiểm toán | Header ghi "only reads", nhưng mỗi lượt chạy có ghi DB. Nó tạo phiên mới và ghi audit `auth.login:password`, `auth.mfa` (`console_store.py:403-405`, `:474-476`). Nó cũng đổi `password_failures`/`totp_last_step` của thành viên (`:397-399`, `:463-470`) và `totp_failures` của phiên (`:502-511`). Chạy runner ngay trước đợt audit sẽ thêm dòng vào trang Nhật ký mà bên audit đang soát. | Sửa câu header thành: không gán/duyệt/đổi vai, nhưng có tạo phiên và ghi audit đăng nhập/MFA/đăng xuất. Thêm một dòng ở phiếu/review-1 để bên audit biết các dòng đó đến từ runner. | Verified | Header đổi thành "không gán/duyệt/đổi vai, nhưng tạo phiên và ghi audit auth.login/auth.mfa/logout"; `review-1.md` mục Runner ghi rõ các dòng Nhật ký đến từ runner. |
| A-4 | P3 | tài-liệu | `ui/DESIGN.md:12-41` (mục "Cấu trúc") | AGENTS.md mục "Submodule" (đổi cấu trúc thì cập nhật DESIGN cùng code) | Diff thêm thư mục `ui/e2e/demos/` (nằm ngoài `src/`) nhưng sơ đồ cấu trúc chưa có. Người đọc DESIGN không biết thư mục này có, cũng không biết nó không thuộc build/vitest. | Thêm một dòng `e2e/demos/  runner chạy tay (Node, không dependency), không thuộc build/vitest — ISSUE-020` ở dưới khối `src/`. | Verified | `ui/DESIGN.md` mục Cấu trúc thêm dòng `e2e/demos/`. |

Trạng thái: `Open` → `Fixed` (fixer) → `Verified` (auditor) · `Reopened` · `Deferred` (P3, kèm hồ sơ theo dõi).

### Theo loại

| Loại | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| đúng-sai | 0 | 0 | 1 | 0 |
| test | 0 | 0 | 0 | 1 |
| tài-liệu | 0 | 0 | 0 | 2 |

## WARN đã xét

Không có WARN.

## Bug đã mở

Không có. A-1 là lỗi của chính file mới trong diff, sửa ngay trong chặng, không phải lỗi hành vi của app. Đã kiểm `bugs/`: chưa có hồ sơ trùng.

## Ngoài phạm vi (nợ cũ nhìn thấy)

- `app/api/rest/routes/console_auth_controller.py:130-134`: `logout` khai `response_model=BaseResponse[LoginState]` nhưng trả `data: []`. Không sai về runtime, nhưng kiểu khai báo thừa.

## Soát lại

Mỗi vòng (lượt auditor) một dòng; tối đa 3 vòng, vòng 2–3 chỉ soát delta của fixer + finding `Fixed`. `Tree` = `git write-tree` của index lúc bắt đầu vòng.

| Lần | Ngày | Tree | Finding đã soát | Kết quả |
|---|---|---|---|---|
| 1 | 2026-10-26 | `b0afa7c40e7a7f81085112f480d62a42ba6d0c06` | A-1…A-4 (audit đầu) | A-1 P2 Open; A-2…A-4 P3 Open |
| 2 | 2026-10-26 | `eb562e4137541cbd241304b52d62975906e1c12e` | A-1…A-4 (delta `git diff --cached b0afa7c4 -- . ':!…/audit-1.md'`: `console-roles.demo.mjs` +29/−9, `ui/DESIGN.md` +1, `review-1.md` đoạn Runner) | A-1…A-4 **Verified**. Không có finding mới. Chi tiết ở mục "Soát lại vòng 2". |

### Soát lại vòng 2 — bằng chứng

- **A-1 Verified.** `normalizeSecret` (`console-roles.demo.mjs:35-39`) đổi sang chữ hoa, bỏ dấu cách và `=`, ký tự ngoài base32 thì trả `null`. `play()` (`:71-75`) thiếu `PASSWORD` hoặc secret hợp lệ thì ghi `L0 BLOCKED` và return; thân vai bọc `try/catch` (`:76-80`), lỗi thành `BLOCKED: <cause.code hoặc message>`\| message>` của riêng vai đó. `out` dùng chung nên các dòng L1/L2 đã ghi vẫn được in. Auditor chạy lại offline `normalizeSecret` + `totp` với vector RFC 6238 (t=59): secret chuẩn → `287082`; `"gezd gnbv …"` (chữ thường, có dấu cách) → `287082`; `""`/`undefined`/`"ABC1"` → `null`, tức BLOCKED. Ca biên: secret dài 1 ký tự (`"A"`) qua được `normalizeSecret` nhưng `totp()` ném lỗi. Lỗi này bị `try/catch` bắt thành `BLOCKED: Cannot read properties of null…` của riêng vai đó, các vai khác không bị ảnh hưởng. Vẫn ra BLOCKED đúng nên không mở finding. `node --check` PASS. Các lượt chạy với console thật (18 ✅, ECONNREFUSED, secret chữ thường → 200) là số liệu của fixer; auditor không chạy lại.
- **A-2 Verified.** Header (`:10-11`) có thêm lưu ý chạy lại sau ≥ 30 s; L4 (`:94`) in gợi ý khi gặp `TOTP_INVALID`. Đúng với cơ chế chống dùng lại mã ở `console_store.py:463-472`.
- **A-3 Verified.** Header (`:5-6`) và `review-1.md:56` đã ghi rõ việc tạo phiên và ghi audit `auth.login`/`auth.mfa`/đăng xuất. Khớp `console_store.py:403-405`, `:474-476`.
- **A-4 Verified.** `ui/DESIGN.md:41` đã có dòng `e2e/demos/`.
- Máy quét `check_diff.py --staged --repo ai`: 0 FAIL, 0 WARN. Auditor **không** stage `audit-1.md` và **không** chạy `--stamp`, vì luật auditor cấm stage. Dấu tính theo digest của index, nên người điều phối cần stage `audit-1.md` trước rồi mới chạy `--stamp`.
