# 🐛 bug-007: Ingest thành công nhưng response lỗi vì đọc duration_ms không tồn tại

> **Đích:** `docs/projects/bugs/bug-007-ingest-response-sai-duration/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

## 📌 Meta

| | |
|---|---|
| **Trạng thái** | ✅ Fixed (đã merge develop) |
| **Mức độ** | P2 |
| **Người báo / Ngày** | Codex root + review agents / 2026-10-15 |
| **Revision** | `origin/khoa-develop` tại `9a1aafd`; so base `6dd8547`, đối chiếu develop `c80037d` |
| **Nguồn** | IPLMS AUDIT-008; nhánh này chưa được nhận vào develop |

## Hành vi thực tế

Handler đọc res.duration_ms nhưng DTO chỉ có process_time (giây). Sau khi await ingestion_service.ingest hoàn tất, response mapping ném AttributeError và catch trảsuccess=False. Người dùng có thể retry dù lần trước service đã ghi draft.

## Hành vi mong đợi

Map đúng process_time sang đơn vịms hoặc dùng DTO hiện hành; success/failure phải phản ánh thao tác thật.

## Tái hiện / bằng chứng

Vị trí **thuộc snapshot9a1aafd**, không phải file develop hiện tại: `app/api/rest/routes/knowledge_controller.py:97; app/core/knowledge/dtos/knowledge_dto.py:IngestResult`. Đọc bằng `git show 9a1aafd:<đường-dẫn>` trong repo AI.

Root lấy AST handler tại9a1aafd, bỏ decorators/type/defaults, stub upload và service trảsynthetic IngestResult-like cóprocess_time0.25. Service đã gọi1 lần; response successFalse, thông báo thiếu duration_ms. Không gọi DB/embedding/LLM, không khẳng định persistence đã kiểm runtime.

## Sửa / kiểm chứng

Map process_time*1000 và kiểm cả SUCCESS/FAILED/duplicate retry; dùng idempotency key ổn định nếu flow cần retry. Chưa sửa.

- [x] Đã sửa và chạy kiểm tập trung tương ứng.
- [x] Đã kiểm tích hợp tại revision nhận vào develop; không lấy source review thay cho runtime.

## Kết quả tích hợp 2026-10-16

process_time*1000, properstatus, uploadbound và UUIDổnđịnh;9RESTtestsPASS vớiservicegiả. Chưa persist/reload trên DBthật; retry có thể tạo draftversionmới. Nguồn: IPLMS ISSUE-124; reviewer độc lập không còn P1/P2 trong phạmvi đã rà. NhánhKhoa gốc không đổi.
