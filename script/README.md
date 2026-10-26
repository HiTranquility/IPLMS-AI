# `script/` — công cụ của repo (không phải của dịch vụ)

Script phục vụ quy trình làm việc và CI, không chạy trong container AI. Lệnh vận hành dịch vụ (seed, eval, tạo admin…) nằm ở [`app/script/`](../app/README.md#script-hay-dùng).

| Script | Làm gì | Chạy |
|---|---|---|
| `board_gen.py` | Sinh `docs/projects/BOARD.md` từ Meta các hồ sơ (IPLMS ADR-0060). Không sửa BOARD bằng tay trong nhánh việc | `python -X utf8 script/board_gen.py --stdout` (xem trước) |
| `check_generated.py` | Chặn PR sửa file sinh tự động (BOARD) | CI `generated-docs.yml` |
| `check_branch_policy.py` + `branch_policy.json` | Kiểm tên nhánh theo mã hồ sơ + tháng tạo và hồ sơ tương ứng có tồn tại | CI `branch-policy.yml`; chạy tay trước khi push |
| `ghcr_retention.py` | Dọn image cũ trên GHCR theo chính sách giữ lại | CI `image-retention.yml` |

Test của chính các script: `python -m unittest script.test_board_gen script.test_branch_policy script.test_ghcr_retention`.
