# 🐛 bug-022: Thuộc tính ảnh chọn khi gán nhãn (mờ, chói, nghiêng…) bị bỏ, không gửi lên server

> **Đích:** `docs/projects/bugs/bug-022-thuoc-tinh-anh-gan-nhan-khong-luu/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code, rà UI trong [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) |
| **Trạng thái** | ✅ Fixed — merge vào develop qua HiTranquility/IPLMS-AI#53 (2026-10-24) / 🟡 |
| **Ngày đóng** | 2026-10-24 |
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

Chủ dự án chốt OPEN-02 = **(a) lưu cờ vào DB** (2026-10-24). Sửa trên nhánh `bugfix/bug-021-2026-10-console-ui-polish` (HiTranquility):

- Schema: `app/infra/database/console_vision_store.py:125-136` thêm cột `vision_label.quality_flags TEXT[] NOT NULL DEFAULT '{}'` bằng `ADD COLUMN IF NOT EXISTS`, cùng CHECK `ck_vision_label_quality_flags` (chỉ nhận `blurry, glare, skewed, occluded, two_line`). Theo đúng cách migrate tại chỗ đang dùng trong store; chạy lại nhiều lần vẫn an toàn. Dòng nhãn cũ nhận mảng rỗng.
- `console_vision_store.py:340,359-361`: `add_label` ghi cờ. `:373,384`: hàng duyệt trả `label.quality_flags`.
- `app/core/console/services/vision_lab_service.py:25-26`: thêm `QUALITY_FLAGS`. `add_label` từ chối cờ lạ, bỏ trùng và giữ thứ tự cố định.
- `app/api/rest/routes/console_vision_controller.py`: `LabelIn.quality_flags` là `List[Literal[...]]`, tối đa 5. `PendingLabel.quality_flags` trả về cho người duyệt.
- UI: `QUALITY_FLAGS`/`QualityFlag` trong `ui/src/types/vision/shares/vision.item.ts`. `addLabel` gửi `quality_flags` (`ui/src/services/apiEndpoints/vision.endpoint.ts`). `LabelWorkspace.tsx:42-64,270-290` gửi cờ đã chọn, nhãn cờ qua i18n (`label.flags`, VI/EN), chip có `aria-pressed`. `ReviewRow.tsx:77-85` hiện cờ cho người duyệt.
- Ô phím tắt trống trên nút "Đúng 100%": `.kbd` dùng `--color-surface-hover` (token không tồn tại) và chữ `--color-text` tối trên nền nút primary tối. Đã đổi sang `color: inherit; border: 1px solid currentColor` (`LabelStudio.module.css:230-240`).
- Test: `test/test_console_vision_lab.py:115,122` (cờ lưu và trả cho người duyệt; cờ lạ bị từ chối, không ghi gì). `ui/src/pages/Vision/Vision.test.tsx` (cờ đã chọn đi cùng body; hai ca cũ thêm `quality_flags: []`).

Kiểm: `python -m unittest test.test_console_vision_lab` trên Postgres 16 cục bộ: 12/12 PASS, chạy lại lần hai trên cùng DB (kiểm migrate idempotent) vẫn PASS. UI: typecheck PASS, vitest 52/52 PASS.

Chưa làm: snapshot/manifest chưa mang cờ, vì thêm vào sẽ đổi `samples_sha256` của golden. Đo ANPR theo điều kiện ảnh (SUGGESTION-004) vẫn chờ Khoa. `ui/src/pages/Vision/components/LabelForm.tsx` không còn được import ở đâu (code chết), chỉ sửa cho qua typecheck, không xoá.
