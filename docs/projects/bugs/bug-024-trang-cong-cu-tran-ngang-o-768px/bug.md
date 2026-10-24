# 🐛 bug-024: Trang Công cụ thử tràn ngang ở khổ 768px

> **Đích:** `docs/projects/bugs/bug-024-trang-cong-cu-tran-ngang-o-768px/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-24 / Claude Code, lượt kiểm bổ sung của [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) |
| **Trạng thái** | ✅ Fixed (chờ PR) / 🟠 |
| **Môi trường** | `develop@5f8e753`, UI dev (`vite`) + API giả `evidence/mock_console_api.py`, Chromium 1243 qua Playwright |

## Hành vi thực tế

Ở khổ 768px, `/tools` có `document.documentElement.scrollWidth = 1013` trong khi viewport chỉ rộng 768, tức trang cuộn ngang 245px. Thẻ thứ ba "Forecast" của khối Chẩn đoán bị đẩy ra ngoài màn hình, còn thẻ "EasyOCR" bị cắt mép phải. Lỗi gặp ở cả theme sáng lẫn tối. Mười màn hình còn lại không tràn.

## Hành vi mong đợi

Không tràn ngang ở 375 / 768 / 1280 (quality gate L5, ngưỡng "tràn ngang = 0").

## Tái hiện

Mở `/tools` ở viewport 768×1024 → cuộn ngang được ([ảnh](../../issues/10-2026/ISSUE-004-ai-console-ui-review/evidence/v2/light-768-tools.png)).

## Bằng chứng

- `ui/src/pages/Tools/components/SystemDiagnostics/SystemDiagnostics.module.css:89-93`: `@media (min-width: 48rem)` chuyển `.cardsGrid` sang `repeat(3, 1fr)`. Mốc 48rem tính theo **viewport** (768px), nhưng sidebar `--rail-width` ở `ui/src/components/layout/AppShell.module.css:1` đã chiếm một phần, nên vùng nội dung chỉ còn khoảng 500px cho 3 cột.
- `1fr` tương đương `minmax(auto, 1fr)`, nên cột không co nhỏ hơn nội dung. Các giá trị monospace như đường dẫn weights hay cache giữ bề rộng tối thiểu và đẩy lưới ra ngoài.
- Đo bằng Playwright: phần tử tràn là `ARTICLE._card_*` (kết quả thô lưu ở scratchpad của phiên, không đưa vào repo).

## Sửa / kiểm chứng

Sửa 2026-10-24 trên nhánh `bugfix/bug-021-2026-10-console-ui-polish` (HiTranquility):

- `ui/src/pages/Tools/components/SystemDiagnostics/SystemDiagnostics.module.css:83-87`: `.cardsGrid` đổi sang `repeat(auto-fit, minmax(min(100%, 14rem), 1fr))`, nên số cột theo bề rộng khối, không theo viewport. `:93`: `.card` có `min-width: 0` để giá trị monospace co lại theo ellipsis có sẵn.

Kiểm: đo lại `scrollWidth` bằng Playwright ở 375/768/1280 × sáng/tối, kết quả ghi ở review-1 (lượt kiểm sau khi gộp các nhánh).
