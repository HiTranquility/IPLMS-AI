# 🐛 bug-021: Trục ngày của biểu đồ Tổng quan Copilot bị cắt còn "Thứ 7", "CN, 1"

> **Đích:** `docs/projects/bugs/bug-021-bieu-do-xu-huong-cat-nhan-ngay/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code, rà UI trong [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) |
| **Trạng thái** | 🆕 New / 🟡 |
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

Chưa sửa.
