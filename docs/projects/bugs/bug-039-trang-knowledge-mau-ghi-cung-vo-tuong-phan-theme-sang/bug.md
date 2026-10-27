# 🐛 bug-039: Trang Knowledge ghi cứng 110 màu, theme sáng tương phản chỉ 1.75–2.56:1

> **Đích:** `docs/projects/bugs/bug-039-trang-knowledge-mau-ghi-cung-vo-tuong-phan-theme-sang/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🆕 New |
| **Người nhận** | |
| **Hạn** | |
| **Ưu tiên** | 🟠 |
| **Ngày đóng** | |
| **Người báo** | Claude ([AUDIT-007](../../audits/10-2026/AUDIT-007-develop-2026-10-27-console-knowledge-settings.md) A1) |
| **Ngày báo** | 2026-10-27 |
| **Môi trường** | develop `e732250` (trang Knowledge vào qua PR #91) |

## Hành vi thực tế

`ui/src/pages/Knowledge/` có 110 màu hex/rgba ghi cứng:

| File | Số chỗ |
|---|---|
| `KnowledgePage.tsx` | 17, trong `style={{}}` ở các dòng 264, 274, 279, 333, 339, 347, 349, 389, 407, 413, 447, 454 |
| `KnowledgePage.module.css` | 53 |
| `components/DocumentPreviewDrawer.module.css` | 38 |
| `components/DocumentPreviewDrawer.tsx` | 2 |

Các màu này lấy từ bảng slate/emerald của theme tối, nên không đổi theo `data-theme`. Ở theme sáng (nền trắng), độ tương phản tính theo WCAG như sau:

| Màu | Dùng cho | Tương phản |
|---|---|---|
| `#34d399` trên `rgba(16,185,129,0.1)` | khối báo nạp thành công (`:407`) | 1.75:1 |
| `#60a5fa` trên `rgba(59,130,246,0.1)` | khối thông tin (`:413`) | 2.26:1 |
| `#94a3b8` | chữ phụ, dung lượng file (`:333`, `:389`, `:447`) | 2.56:1 |
| `#10b981` | số liệu trạng thái (`:279`) | 2.54:1 |
| `#ef4444` | nút "Xoá" file (`:339`) | 3.76:1 |

Tất cả đều dưới ngưỡng 4.5:1 cho chữ thường.

## Hành vi mong đợi

Màu chỉ đi qua token (`ui/DESIGN.md:80`, luật 8), và cả hai theme đều đạt tối thiểu 4.5:1 như các trang khác (ai bug-025).

## Tái hiện

1. Bật theme sáng, mở `/knowledge`.
2. Nạp một file. Dòng báo thành công màu xanh gần như không đọc được.
3. Lệnh đếm: `grep -cE '#[0-9a-fA-F]{3,8}\b|rgba?\(' ui/src/pages/Knowledge/KnowledgePage.tsx ui/src/pages/Knowledge/*.css ui/src/pages/Knowledge/components/*`

## Sửa / kiểm chứng

- Thay bằng token trong `ui/src/index.css`: `--color-muted`, `--color-success`/`--color-success-soft`, `--color-danger`/`--color-danger-soft`, `--color-info`, `--color-accent-dark`. Dời `style={{}}` sang module CSS.
- Kiểm chứng: lệnh đếm ở trên ra 0, và đo tương phản ở cả hai theme (cổng chất lượng L2 theo IPLMS ADR-0041).
