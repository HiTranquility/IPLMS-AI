# 🐛 bug-006: Không có model vẫn trả loại xe suy từ biển như nhận dạng ảnh

> **Đích:** `docs/projects/bugs/bug-006-vehicle-prior-gia-lam-observation/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

## 📌 Meta

| | |
|---|---|
| **Trạng thái / Mức độ** | 🆕 New — phát hiện trên nhánh chưa merge / P1 |
| **Người báo / Ngày** | Codex root + review agents / 2026-10-15 |
| **Revision** | `origin/khoa-develop` tại `9a1aafd`; so base `6dd8547`, đối chiếu develop `c80037d` |
| **Nguồn** | IPLMS AUDIT-008; nhánh này chưa được nhận vào develop |

## Hành vi thực tế

Khi _ensure_loaded=False, classify_vehicle trả plate_prior. Thử ảnh rỗng b"" vẫn trảcar_sedan với51F12345, motorbike với59V179379, truck với51C12345. Prior xe máy/xe tải còn lấn kết quả CNN. Loại xe được gán vào kết quả ANPR mà không phân biệt suy đoán hay quan sát, làm bằng chứng đối chiếu loại xe có thể thành vòng tròn.

## Hành vi mong đợi

Thiếu model/ảnh hợp lệ phải giữ unknown/None; prior có field riêng và không được dùng như bằng chứng hình ảnh cho anti-fraud.

## Tái hiện / bằng chứng

Vị trí **thuộc snapshot9a1aafd**, không phải file develop hiện tại: `app/core/vision/engines/vehicle_classifier.py:109–112,137–147; app/core/vision/services/anpr_service.py:53–61`. Đọc bằng `git show 9a1aafd:<đường-dẫn>` trong repo AI.

Root chạy riêng AST classify_vehicle; thay loader bằng lambdaFalse, logger bằng stub, bỏ import app.util.logger; không import app/config/torch hay đọc checkpoint. Tái hiện đủ3 kết quả trên. Chưa chạy anti-fraud E2E; tác động caller từ đối chiếu source.

## Sửa / kiểm chứng

Giữ guard None của develop; nếu muốn prior phải đề xuất hợp đồng DTO/proto và confidence/provenance riêng trước. Không tự đổi schema/hợp đồng trong review. Chưa sửa.

- [ ] Đã sửa và chạy kiểm tập trung tương ứng.
- [ ] Đã kiểm tích hợp tại revision nhận vào develop; không lấy source review thay cho runtime.
