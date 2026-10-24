# 🐛 bug-021: Trục ngày của biểu đồ Tổng quan Copilot bị cắt còn "Thứ 7", "CN, 1"

> **Đích:** `docs/projects/bugs/bug-021-bieu-do-xu-huong-cat-nhan-ngay/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code, rà UI trong [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) |
| **Trạng thái** | ✅ Fixed — merge vào develop qua HiTranquility/IPLMS-AI#53 (2026-10-24) / 🟡 |
| **Môi trường** | `develop@5f8e753` |

## Hành vi thực tế

Nhãn trục X là `fmtDay(date).slice(0, 5)`. Với `vi-VN`, `fmtDay` trả "Thứ 7, 10/10" nên còn "Thứ 7", và trả "CN, 11/10" nên còn "CN, 1". Với `en-US`, "Sat, 10/10" còn "Sat, ". Trên trục không còn ngày nào: 14 cột chỉ hiện thứ trong tuần lặp lại hai lần, và nhãn Chủ nhật có thêm một chữ số thừa.

## Hành vi mong đợi

Nhãn trục hiện ngày/tháng (ví dụ `10/10`). Thứ trong tuần chỉ hiện trong tooltip hoặc dòng chi tiết. Không cắt chuỗi đã được Intl định dạng, vì độ dài thay đổi theo locale.

## Tái hiện

Mở `/` với dữ liệu 14 ngày từ 10/10 tới 23/10 → trục hiện `Thứ 7, CN, 1, Thứ 2, …` ([ảnh](../../issues/10-2026/ISSUE-004-ai-console-ui-review/evidence/02-overview.png)).

## Bằng chứng

- `ui/src/pages/Overview/components/TrendChart.tsx:196`: `.slice(0, 5)`.
- `ui/src/utils/format.ts:14,28`: định dạng `weekday short + day + month`.
- Cùng file, dòng 222, có chữ "lượt hỏi" viết cứng không qua i18n. Dòng tóm tắt gọi lượt `SUCCESS` là "đúng", trong khi trang này nói rõ tỉ lệ đúng chỉ tính trên lượt đã chấm.

## Sửa / kiểm chứng

Sửa 2026-10-24 trên nhánh `bugfix/bug-021-2026-10-console-ui-polish` (HiTranquility):

- `ui/src/utils/format.ts:31`: thêm `fmtDayMonth`. Hàm lấy phần ngày và tháng bằng `formatToParts` rồi tự nối bằng `/`, vì ICU của `vi-VN` cho ra `11-10` trên Node nhưng `11/10` trên Chrome. Không còn cắt chuỗi.
- `ui/src/pages/Overview/components/TrendChart.tsx:196`: trục X dùng `fmtDayMonth`. `:222-238`: tooltip bỏ "lượt hỏi/đúng/chặn/lỗi" viết cứng, dùng `t.overview.turnCount` và nhãn chú giải ("Thành công / Bị chặn / Lỗi"), nên không còn gọi lượt `SUCCESS` là "đúng".
- Test: `ui/src/utils/format.test.ts` (vi → `11/10`, en → `10/11`).

Kiểm: `pnpm typecheck` PASS; `npx vitest run --maxWorkers=1` 13 file / 52 test PASS.
