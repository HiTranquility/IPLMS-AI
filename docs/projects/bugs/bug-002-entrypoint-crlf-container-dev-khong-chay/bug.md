# 🐛 bug-002: `docker-entrypoint.sh` bị CRLF trên Windows → container `ai` dev chết ngay khi khởi động

> **Đích:** `docs/projects/bugs/bug-002-entrypoint-crlf-container-dev-khong-chay/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)
> Gặp khi chạy E2E cho PROB-046 phase 2 (repo gốc), ngày 2026-10-07.

| | |
|---|---|
| **Trạng thái** | ✅ Fixed — container `ai` dev lên `healthy` sau khi sửa |
| **Người báo** | Claude (lúc dựng stack dev để chạy E2E) |
| **Môi trường** | Windows 11, Docker Desktop, checkout có `core.autocrlf=true`; `docker compose -f docker-compose.yml -f docker-compose.develop.yml` |

## Hành vi thực tế

Tạo container theo đúng hướng dẫn của `docker-compose.develop.yml`, container `ai` thoát ngay, log chỉ có một dòng:

```text
exec /usr/local/bin/docker-entrypoint.sh: no such file or directory
```

## Nguyên nhân gốc

- `git ls-files --eol docker-entrypoint.sh` → `i/lf w/crlf attr/`: trong git là LF, nhưng `core.autocrlf=true` đổi bản trên máy thành CRLF. `.gitattributes` chỉ khai `*.pdf`/`*.docx` binary, không khai `*.sh`.
- Override dev **mount thẳng** `./docker-entrypoint.sh` vào container, nên dòng shebang thành `#!/bin/bash<CR>`, và kernel tìm một interpreter tên `bash\r` không tồn tại.
- Image build từ `docker-compose.yml` không mount file này nên không thấy lỗi. Container cũ trên máy dev hoá ra được tạo **không có** override, tức là đang chạy code đóng gói trong image chứ không phải code đang sửa. Đây là một bẫy riêng: sửa code mà container không đổi.

## Sửa

- `.gitattributes`: `*.sh text eol=lf`. `docker-entrypoint.sh` và `setup-dev.sh` được chuyển lại LF trong working copy (nội dung trong git không đổi).
- Kiểm chứng: `git ls-files --eol` → `w/lf attr/text eol=lf`; `up -d --no-deps --no-build --force-recreate ai` → `running/healthy`, container thấy code mới (grep `injection_flags` trong `/app/app/...` có kết quả).

## Ghi chú

Clone khác trên Windows sẽ tự nhận LF ở lần checkout tiếp theo nhờ `.gitattributes`. Riêng clone đã có sẵn thì chạy `git checkout -- docker-entrypoint.sh setup-dev.sh`, hoặc chuyển file về LF một lần.
