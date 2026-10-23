# 🐛 bug-022: Thuộc tính ảnh chọn khi gán nhãn (mờ, chói, nghiêng…) bị bỏ, không gửi lên server

> **Đích:** `docs/projects/bugs/bug-022-thuoc-tinh-anh-gan-nhan-khong-luu/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code, rà UI trong [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) |
| **Trạng thái** | 🆕 New / 🟡 |
| **Môi trường** | `develop@5f8e753` |

## Hành vi thực tế

Màn Gán nhãn có khối "Thuộc tính ảnh / biển số" với 5 lựa chọn: Biển mờ / bụi bẩn, Chói sáng đèn pha, Góc chụp nghiêng, Che khuất một phần, Biển 2 dòng. Người gán chọn xong, nhưng `send()` chỉ gửi `{verdict, plate_text}` lên `POST /vision/samples/{id}/labels`. Gửi thành công thì `setQualityFlags([])` xoá luôn lựa chọn. Thao tác của người gán mất hẳn, và giao diện không cho thấy điều đó.

## Hành vi mong đợi

Chốt một trong hai:

- (a) Lưu thuộc tính cùng nhãn. Việc này cần thêm cột hoặc bảng và API, nên phải qua `iplms-schema-design`. Lợi ích là đo được độ chính xác ANPR theo từng điều kiện ảnh, xem [SUGGESTION-004](../../suggestions/10-2026/SUGGESTION-004-luu-thuoc-tinh-anh-khi-gan-nhan.md).
- (b) Gỡ khối thuộc tính khỏi UI cho tới khi có (a).

## Tái hiện

Đọc `ui/src/pages/Vision/components/LabelStudio/LabelWorkspace.tsx:56-70` (`send`) và `:139-145` (danh sách cờ), rồi đối chiếu `ui/src/services/apiEndpoints/vision.endpoint.ts` (`addLabel` chỉ có `verdict`, `plate_text`). Ảnh màn hình: `../../issues/10-2026/ISSUE-004-ai-console-ui-review/evidence/08-label.png`.

## Bằng chứng

Như trên. Nút "Đúng 100%" có một ô vuông trống ở chỗ đáng lẽ hiện phím tắt `1` (cùng ảnh). Đây là lỗi hiển thị nhỏ, sửa chung với bug này được.

## Sửa / kiểm chứng

Chưa sửa.
