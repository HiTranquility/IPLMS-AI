# 🌱 SUGGESTION-004: Lưu thuộc tính ảnh khi gán nhãn để đo ANPR theo điều kiện ảnh

> **Đích:** `docs/projects/suggestions/10-2026/SUGGESTION-004-luu-thuoc-tinh-anh-khi-gan-nhan.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🔄 REVIEWING |
| **Ưu tiên** | 🟢 |
| **Ngày** | 2026-10-23 |
| **Người đề xuất** | Claude Code ([ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md)) |
| **Techlead duyệt** | @HiTranquility — ⏳ chờ |
| **Làm trước khi duyệt?** | Không: đổi schema và API |
| **Phạm vi** | `ai/` (bảng nhãn console, API `/vision/samples/{id}/labels`, Tổng quan Vision) |

## Đề xuất

Lưu các cờ `blurry | glare | skewed | occluded | two_line | night` cùng nhãn. Trang Tổng quan Vision thêm bảng "độ chính xác máy theo điều kiện ảnh", có khoảng tin cậy 95% giống chỉ số hiện có. Snapshot train có thể lọc hoặc cân bằng theo cờ.

## Vấn đề nó giải quyết

Hiện thao tác chọn cờ bị bỏ ([bug-022](../../bugs/bug-022-thuoc-tinh-anh-gan-nhan-khong-luu/bug.md)). Khoa đang calibration confidence theo camera (IPLMS PROB-045). Có cờ điều kiện ảnh thì biết model hỏng ở đâu (biển 2 dòng, chói đèn) để thu thêm dữ liệu đúng chỗ.

## Phạm vi

- Trong: đề xuất schema qua `iplms-schema-design` trước khi code, API, UI và báo cáo.
- Ngoài: tự động suy cờ bằng model.

## Bằng chứng / tham khảo

`ui/src/pages/Vision/components/LabelStudio/LabelWorkspace.tsx:56-70,139-145`.

## Bước tiếp theo

Khoa xác nhận bộ cờ có giá trị cho calibration, rồi mở ISSUE. Schema do người phụ trách DB console duyệt; phần UI giao Phát.
