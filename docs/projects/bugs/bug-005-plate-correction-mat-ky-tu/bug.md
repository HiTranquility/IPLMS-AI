# 🐛 bug-005: Hiệu chỉnh biển số cắt mất ký tự nhưng giữ confidence

> **Đích:** `docs/projects/bugs/bug-005-plate-correction-mat-ky-tu/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

## 📌 Meta

| | |
|---|---|
| **Trạng thái / Mức độ** | ✅ Fixed trong nhánh tích hợp — chưa merge / P1 |
| **Người báo / Ngày** | Codex root + review agents / 2026-10-15 |
| **Revision** | `origin/khoa-develop` tại `9a1aafd`; so base `6dd8547`, đối chiếu develop `c80037d` |
| **Nguồn** | IPLMS AUDIT-008; nhánh này chưa được nhận vào develop |

## Hành vi thực tế

Hàm correct_vietnamese_plate nhận 59V179379 trả59V-179.37; nhận51F-178.I2 trả51F-178. Regex ô tô chạy trước xe máy, khớp một phần rồi cắt dãy số. run_anpr luôn áp sửa lên winner mà giữ confidence cũ; có thể đổi danh tính biển gửi backend.

## Hành vi mong đợi

Không cắt ký tự để ép thành mẫu; giữ raw OCR, chỉ chuẩn hóa khi toàn chuỗi khớp không mơ hồ. Confidence/provenance phải phản ánh hiệu chỉnh.

## Tái hiện / bằng chứng

Vị trí **thuộc snapshot9a1aafd**, không phải file develop hiện tại: `app/core/vision/engines/anpr_engine.py:155–169,779–780`. Đọc bằng `git show 9a1aafd:<đường-dẫn>` trong repo AI.

Root và agent chạy riêng hàm lấy bằng git show9a1aafd qua ast +stdlib; chỉ nạp literal mapping và re, không import app/config/model. Hai kết quả trên tái hiện chính xác. Đây là logic test cô lập, chưa phải đo ANPR trên ảnh.

## Sửa / kiểm chứng

Port normalization vào parser hiện hành, thêm fixture biển xe máy/hai dòng/OCRnhầm/các chuỗi dư ký tự; không overwrite monolith lên engine ONNX hiện tại. Chưa sửa.

- [ ] Đã sửa và chạy kiểm tập trung tương ứng.
- [ ] Đã kiểm tích hợp tại revision nhận vào develop; không lấy source review thay cho runtime.

## Kết quả tích hợp 2026-10-16

Loại correctionlossy, giữ parserdevelop và candidateconfidence/cropgốc; portpreprocess có fixturetổnghợp. Vision60testsPASS; chưa benchmarkảnhthật. Nguồn: IPLMS ISSUE-124; reviewer độc lập không còn P1/P2 trong phạmvi đã rà. NhánhKhoa gốc không đổi.
