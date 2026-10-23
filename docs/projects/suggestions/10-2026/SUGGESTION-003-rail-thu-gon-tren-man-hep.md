# 🌱 SUGGESTION-003: Thu sidebar thành ngăn kéo trên màn hẹp

> **Đích:** `docs/projects/suggestions/10-2026/SUGGESTION-003-rail-thu-gon-tren-man-hep.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🔄 REVIEWING |
| **Ngày** | 2026-10-23 |
| **Người đề xuất** | Claude Code ([ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md)) |
| **Techlead duyệt** | @HiTranquility — ⏳ chờ |
| **Làm trước khi duyệt?** | Có thể: việc nhỏ, chỉ đổi UI, revert được |
| **Phạm vi** | `ai/ui` (`components/layout/AppShell*`) |

## Đề xuất

Dưới 768px, sidebar chuyển thành ngăn kéo, mở bằng nút menu ở thanh trên. Thanh trên giữ tên trang và nút ngôn ngữ/theme.

## Vấn đề nó giải quyết

Ở 375×812, sidebar xếp chồng lên trên và chiếm trọn màn đầu: `main` bắt đầu ở y = 812px. Người gán nhãn hoặc duyệt trên tablet/điện thoại phải cuộn qua 13 mục menu mới tới việc của mình. Không có tràn ngang (`scrollWidth` = 375), bảng audit cuộn trong khung của nó.

## Phạm vi

- Trong: AppShell, focus trap và Esc cho ngăn kéo, test layout ở 375/768.
- Ngoài: thiết kế lại từng trang cho mobile.

## Bằng chứng / tham khảo

Đo bằng browser pane ngày 2026-10-23 trên `/vision/label` và `/audit`: `document.querySelector('main').getBoundingClientRect().top === 812.5`.

## Bước tiếp theo

Giao Phát.
