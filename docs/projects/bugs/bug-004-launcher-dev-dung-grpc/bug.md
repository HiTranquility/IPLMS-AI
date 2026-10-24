# 🐛 bug-004: Launcher dev dừng AI/gateway nhưng chỉ khởi động REST

> **Đích:** `docs/projects/bugs/bug-004-launcher-dev-dung-grpc/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

## 📌 Meta

| | |
|---|---|
| **Trạng thái** | ✅ Fixed (đã merge develop) |
| **Mức độ** | P2 |
| **Người báo / Ngày** | Codex root + review agents / 2026-10-15 |
| **Revision** | `origin/khoa-develop` tại `9a1aafd`; so base `6dd8547`, đối chiếu develop `c80037d` |
| **Nguồn** | IPLMS AUDIT-008; nhánh này chưa được nhận vào develop |

## Hành vi thực tế

Launcher stop ai và gateway rồi chạy uvicorn app.main:app; không khởi động app.grpc_server. REST/dashboard có thể hoạt động trong khi backend mất đích gRPC50051. Shell nuốt lỗi Docker bằng ||true rồi in thành công; PowerShell không kiểm LASTEXITCODE cho lệnh đó.

## Hành vi mong đợi

Launcher toàn bộ phải giữ cả REST/gRPC hoặc công bố rõ dashboard-only và không dừng stack đang phục vụ. Báo thành công sau khi dependency sẵn sàng.

## Tái hiện / bằng chứng

Vị trí **thuộc snapshot9a1aafd**, không phải file develop hiện tại: `start-dev.ps1:22–25,57; start-dev.sh:13–15,38`. Đọc bằng `git show 9a1aafd:<đường-dẫn>` trong repo AI.

Đọc script tại9a1aafd và app/main.py: lifespan chỉ warmup, không spawn gRPC; backend/src/infrastructures/Ai/ai.module.ts:34 dùng AI_GRPC_URL. Chưa chạy script vì sẽ dừng container dùng chung.

## Sửa / kiểm chứng

Quản lý vòng đời hai process hoặc giữ Docker; kiểm exitcode và DB readiness với timeout. Kiểm REST lẫn gRPC và tình huống Docker/network lỗi bằng fixture local. Chưa sửa.

- [x] Đã sửa và chạy kiểm tập trung tương ứng.
- [x] Đã kiểm tích hợp tại revision nhận vào develop; không lấy source review thay cho runtime.

## Kết quả tích hợp 2026-10-16

Native supervisor chạyREST+gRPC, bindloopback, không stop/start sharedDocker, busyport/failure/cleanup có6testsPASS. Không báo DBready dựa vào việc gọi Docker. Nguồn: IPLMS ISSUE-124; reviewer độc lập không còn P1/P2 trong phạmvi đã rà. NhánhKhoa gốc không đổi.
