# proto/ — bản chép hợp đồng gRPC dùng để build image và chạy CI

Nguồn chuẩn là `proto/` ở **gốc repo cha `IPLMS`**. Bản chép ở đây là thứ
`Dockerfile` (context = repo này, [ADR-0006](../docs/projects/adrs/10-2026/0006-build-context-la-repo-ai.md))
và `.github/workflows/ci.yml` dùng để sinh stub, nên clone riêng IPLMS-AI vẫn build được.

- `app/script/compile_proto.py` tìm `../proto` **trước**: chạy native trong monorepo
  thì dùng bản umbrella; trong image chỉ có bản này (`/app/proto`).
- [NEVER] sửa tay ở đây. Đổi hợp đồng → sửa `IPLMS/proto/` → chép sang đây **cùng đợt**.
- Lệch được bắt bởi `IPLMS/proto/check_proto_sync.py` (CI repo cha).
