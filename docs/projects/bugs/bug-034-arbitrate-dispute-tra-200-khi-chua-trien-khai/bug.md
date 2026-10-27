# 🐛 bug-034: Endpoint arbitrate-dispute trả HTTP 200 khi ném FeatureNotImplementedError

> **Đích:** `docs/projects/bugs/bug-034-arbitrate-dispute-tra-200-khi-chua-trien-khai/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed |
| **Người nhận** | @HiTranquility |
| **Hạn** | 2026-10-31 |
| **Ưu tiên** | 🟡 |
| **Ngày đóng** | 2026-10-26 |
| **Người báo** | Antigravity AI Fuzzing Agent |
| **Ngày báo** | 2026-10-26 |
| **Môi trường** | local / develop |

## Hành vi thực tế

Khi gọi `POST /api/copilot/arbitrate-dispute`, `copilot_service.arbitrate_dispute` ném `FeatureNotImplementedError` theo nguyên tắc "Thà lỗi hơn bịa" (ADR-0008). Tuy nhiên, controller trong `app/api/rest/routes/copilot_controller.py` bắt ngoại lệ này và trả về một dict raw:
```json
{
  "success": false,
  "status": "UNIMPLEMENTED",
  "message": "Thẩm định tranh chấp bằng AI chưa khả dụng...",
  "safety_rule": "..."
}
```
với mã HTTP status **200 OK** thay vì HTTP 501 Not Implemented (hoặc 422/500).

## Hành vi mong đợi

1. Một thao tác chưa được triển khai hoặc bị từ chối nghiệp vụ không được trả HTTP 200 OK. Phải trả HTTP **501 Not Implemented** hoặc sử dụng cấu trúc chuẩn `BaseResponse.fail(...)` kèm mã lỗi thích hợp.
2. Trả HTTP 200 cho một request thất bại khiến các HTTP client (Axios, NestJS gRPC caller, fetch client) không kích hoạt logic `catch`/`onError` chuẩn và dễ dẫn đến sai lệch trạng thái nghiệp vụ.

## Tái hiện

1. Chạy container gateway / api hoặc local server.
2. Thực thi POST request:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/copilot/arbitrate-dispute \
     -H "Content-Type: application/json" \
     -d '{"dispute_id": "DSP-1002", "session_id": "sess-8891", "claim_reason": "Barie kẹt", "claimed_amount": 35000}'
   ```
3. Quan sát HTTP status trả về là `200` thay vì `501`.
4. Dẫn chứng code: [copilot_controller.py#L225-L246](file:///C:/Users/Admin/Downloads/IPLMS/ai/app/api/rest/routes/copilot_controller.py#L225-L246)

## Bằng chứng

Log kiểm thử từ bộ adversarial fuzzing battery:
```
Status: 200
Body: {"success":false,"status":"UNIMPLEMENTED","message":"Thẩm định tranh chấp bằng AI chưa khả dụng: phần đối chiếu quy chế và log phiên đỗ chưa được triển khai. Vui lòng xử lý khiếu nại thủ công.","safety_rule":"Thà lỗi hơn bịa (ADR-0008): Hệ thống từ chối tự động hoàn tiền khi chưa có model đối chiếu video log và quy chế thật."}
```

## Sửa / kiểm chứng

1. **Cập nhật mã trạng thái HTTP trong controller:**
   - Trong `app/api/rest/routes/copilot_controller.py`, khi bắt ngoại lệ `FeatureNotImplementedError`, trả về:
     ```python
     return JSONResponse(
         status_code=status.HTTP_501_NOT_IMPLEMENTED,
         content={
             "success": False,
             "status": "UNIMPLEMENTED",
             "message": str(exc),
             "safety_rule": "Thà lỗi hơn bịa (ADR-0008): Hệ thống từ chối tự động hoàn tiền khi chưa có model đối chiếu video log và quy chế thật.",
         },
     )
     ```
   - Khi có ngoại lệ không mong muốn, trả về `HTTP_500_INTERNAL_SERVER_ERROR`.
2. **Kiểm chứng:**
   - Đã kiểm tra lại qua script fuzzing: `POST /copilot/arbitrate-dispute` trả về chính xác mã `501 Not Implemented`.
   - Client HTTP bắt được lỗi theo chuẩn REST thay vì bị nhầm lẫn bởi mã `200 OK`.
