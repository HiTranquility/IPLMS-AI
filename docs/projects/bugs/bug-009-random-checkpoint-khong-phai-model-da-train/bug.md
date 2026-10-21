# 🐛 bug-009: Generator mới tạo checkpoint ngẫu nhiên vào đường model phục vụ

> **Đích:** `docs/projects/bugs/bug-009-random-checkpoint-khong-phai-model-da-train/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái / Mức độ** | ✅ Fixed trong nhánh tích hợp — chưa merge / P2 |
| **Ngày / Người báo** | 2026-10-16 / Codex |
| **Nguồn** | IPLMS ISSUE-124 / AUDIT-008 |

## Hành vi / bằng chứng

Nhánh Khoa9a1aafd có `training/create_vehicle_checkpoint.py:17–48`: khởi tạo NetV2, Kaiming/normal ngẫu nhiên, gắn version/labels rồi ghi `model/checkpoint/vehicle-classifier.pth`. Không có huấn luyện/đánh giá. Khi người dùng chạy script này, nó có thể ghi đè artifact ở đường phục vụ; file có đúngshape không chứng minh model nhận dạng được.

Chỉ đọc code, không chạy generator và không truy cập/ghi checkpoint thật. Không kết luận máy hiện có checkpoint ngẫu nhiên.

## Xử lý

Loại phần thêm generator khỏi merge tích hợp; giữ nhánh Khoa gốc để truy lịch sử. Guide mới nói rõ không dùng checkpoint khởi tạo ngẫu nhiên thay model đã train. Classifier giữ strict/min-confidence và thiếumodel→None. Không thêm model/weights; cần gate đo ảnh thật trước rollout.
