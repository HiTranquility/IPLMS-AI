# 🐛 bug-025: Chữ màu `--color-faded` và chữ màu accent dưới ngưỡng tương phản AA

> **Đích:** `docs/projects/bugs/bug-025-mau-chu-faded-va-accent-duoi-nguong-tuong-phan/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-24 / Claude Code, lượt kiểm bổ sung của [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) |
| **Trạng thái** | 🆕 New / 🟠 |
| **Môi trường** | `develop@5f8e753`, UI dev + API giả, Chromium 1243, đo ở theme sáng 1280 và theme tối 768 |

## Hành vi thực tế

Quality gate L4/L6 đòi chữ thường đạt ≥ 4.5:1 ở mọi theme. Lượt đo tự động trên 11 màn hình (lấy màu chữ đã tính so với nền đục gần nhất) cho thấy các trường hợp không đạt:

| Màu chữ | Token / chỗ dùng | Nền | Tỉ lệ | Ở đâu |
|---|---|---|---|---|
| `#85827a` | `--color-faded` (sáng) | surface `#ffffff` | 3.84 | Tiêu đề nhóm sidebar (Copilot/Vision/Quản trị), dòng phụ thẻ số ở Tổng quan, phần trăm phân bố… có trên mọi màn |
| `#77746d` | `--color-faded` (tối) | surface `#1a1a19` | 3.74 | Như trên, ở theme tối |
| `#d97706` | `--color-accent` (sáng) dùng làm **màu chữ** | `#fff` / accent-soft | 3.19 / 2.77 | Nút "Làm mới", giá trị trong thẻ Chẩn đoán (`14.2 MB`, `["en","vi"]`, `CPU`), dòng phụ "Nội bộ · IPLMS" |
| `#15803d` | `--color-success` | success-soft / surface-2 | 4.36–4.42 | Nhãn `READY`, tiêu đề 4 quy chuẩn ở Tools |
| `#a16207` | `--color-warning` | warning-soft | 4.28 | "· 3 chặn" ở Tổng quan |

Theme tối chỉ có lỗi ở `--color-faded`. Accent `#f59e0b` trên nền tối đạt ngưỡng.

## Hành vi mong đợi

Mọi chữ ≥ 4.5:1 (chữ lớn ≥ 3:1) ở cả hai theme. Accent sáng chỉ dùng cho viền, vòng focus và nền; chữ màu nhấn dùng `--color-accent-dark` (`#92400e`).

## Tái hiện

Mở `/` và `/tools` ở theme sáng, so màu chữ của tiêu đề nhóm sidebar và nút "Làm mới" với nền ([ảnh sáng](../../issues/10-2026/ISSUE-004-ai-console-ui-review/evidence/v2/light-1280-tools.png), [ảnh tối](../../issues/10-2026/ISSUE-004-ai-console-ui-review/evidence/v2/dark-768-overview.png)).

## Bằng chứng

- `ui/src/index.css:15` (`--color-faded: #85827a`), `ui/src/index.css:50` (`--color-faded: #77746d`), `ui/src/index.css:25` (`--color-accent: #d97706`), `:30`, `:32`.
- `color: var(--color-accent)` xuất hiện 54 lần trong 17 file CSS, ví dụ `ui/src/pages/Tools/components/SystemDiagnostics/SystemDiagnostics.module.css:56,184`, `ui/src/components/layout/AppShell.module.css:42`. `var(--color-faded)` xuất hiện 42 lần, nhiều nhất ở `ChatStudio.module.css` (14 lần).
- `ui/src/pages/Members/components/RoleBadge.module.css:61` viết cứng `#d97706`.

## Sửa / kiểm chứng

Chưa sửa. Hướng gợi ý: tối thiểu thì làm đậm `--color-faded` (sáng khoảng `#6e6b63`, tối khoảng `#949189`; đo trên surface-2 vì nhiều chữ faded nằm trên nền này) và đổi chữ dùng accent sang `--color-accent-dark`, rồi đo lại tỉ lệ ở cả hai theme. Đổi token phải cập nhật `ui/DESIGN.md` cùng lúc.
