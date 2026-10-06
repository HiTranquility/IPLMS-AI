# proto/ — bản sao cho CI repo AI đứng riêng

Nguồn chuẩn là `proto/` ở **gốc repo cha `IPLMS`**. Thư mục này chỉ tồn tại để
`.github/workflows/ci.yml` của repo AI (checkout một mình, không có `../proto`)
sinh được stub và chạy test.

- `app/script/compile_proto.py` tìm `../proto` **trước**, nên trong monorepo và
  khi build Docker (context = gốc repo cha) bản này **không được dùng**.
- [NEVER] sửa tay ở đây. Đổi hợp đồng → sửa `IPLMS/proto/` → chép sang đây.
- Lệch được bắt bởi `IPLMS/proto/check-proto-sync.py` (CI repo cha).
