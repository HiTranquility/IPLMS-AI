# 🐛 bug-003: Docker context mới làm gãy CI và đưa dữ liệu runtime vào image

> **Đích:** `docs/projects/bugs/bug-003-docker-context-khong-dong-bo/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

## 📌 Meta

| | |
|---|---|
| **Trạng thái / Mức độ** | 🆕 New — phát hiện trên nhánh chưa merge / P1 |
| **Người báo / Ngày** | Codex root + review agents / 2026-10-15 |
| **Revision** | `origin/khoa-develop` tại `9a1aafd`; so base `6dd8547`, đối chiếu develop `c80037d` |
| **Nguồn** | IPLMS AUDIT-008; nhánh này chưa được nhận vào develop |

## Hành vi thực tế

Nhánh bỏ tiền tố ai/ trong COPY và chuyển Compose context sang ai/. CI image vẫn checkout dưới ai/, build context gốc và dùng ai/Dockerfile; COPY requirements-service.txt không tìm thấy file ở root. Backend compose và script registry cũng dùng contract context gốc. Nếu chạy context ai mới, root .dockerignore không còn áp dụng; COPY static/data có thể mang ảnh original/cropped và dữ liệu local vào image. Không đọc hoặc xác nhận máy này có dữ liệu đó.

## Hành vi mong đợi

Build contract phải nhất quán ở mọi caller, context có allowlist và không chứa ảnh/dữ liệu runtime ngoài danh sách chủ động.

## Tái hiện / bằng chứng

Vị trí **thuộc snapshot9a1aafd**, không phải file develop hiện tại: `Dockerfile:21,25–29,51; docker-compose.yml:27–28; ai/.dockerignore (chỉ comment)`. Đọc bằng `git show 9a1aafd:<đường-dẫn>` trong repo AI.

Đối chiếu git show 9a1aafd:Dockerfile với .github/workflows/image.yml:43–49,70–71,112–113 cùng revision; caller hiện hành backend/docker-compose.yml:247–248 và deployment/registry/push-images-local.ps1:18. Root .dockerignore loại static/original, static/cropped và data trừ corpus knowledge; ai/.dockerignore không có rule. Không build Docker hoặc quét dữ liệu thật.

## Sửa / kiểm chứng

Giữ context gốc và COPY ai/ hiện hành. Nếu hỗ trợ clone độc lập, thiết kế riêng rồi cập nhật CI/caller và allowlist cùng đợt. Kiểm build/context/image bằng fixture giả trước khi nhận. Checkpoint đã có thể được COPY từ trước, không tính đó là regression mới.

- [ ] Đã sửa và chạy kiểm tập trung tương ứng.
- [ ] Đã kiểm tích hợp tại revision nhận vào develop; không lấy source review thay cho runtime.
