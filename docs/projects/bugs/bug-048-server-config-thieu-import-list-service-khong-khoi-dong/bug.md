# 🐛 bug-048: `server_config.py` mất `from typing import List` sau merge, `app.config` lỗi `NameError` nên service AI không khởi động

> **Đích:** `docs/projects/bugs/bug-048-server-config-thieu-import-list-service-khong-khoi-dong/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🛠️ Fixing — đã sửa trên `bugfix/bug-048-2026-10-server-config-thieu-import-list`, chờ PR |
| **Người nhận** | @HiTranquility |
| **Ưu tiên** | 🔴 |
| **Người báo** | Claude Code, phát hiện khi làm ISSUE-026 (red-team agent) |
| **Ngày báo** | 2026-10-28 |
| **Môi trường** | develop `427c07f` (sau PR #115); `main` không bị |

## Hành vi thực tế

`app/config/server_config.py:28` khai báo `def cors_allow_origin_list(self) -> List[str]` nhưng file không có `from typing import List` và không có `from __future__ import annotations`. Annotation được tính ngay khi tạo class, nên `import app.config` ném `NameError: name 'List' is not defined`. Mọi entrypoint (gRPC, FastAPI, script) đều đi qua `app.config`, nên service không khởi động được.

Gốc: commit bug-045 (`f7ff908`) có dòng import; merge giải conflict `4a27ba1` (PR #115) xoá dòng đó nhưng giữ phương thức dùng `List`.

Cùng loại, không làm sập lúc chạy (module có `from __future__ import annotations`) nhưng lint F821: `app/core/copilot/engines/rag_pipeline.py:103,122,344,387` (`List`, `Optional`), `app/core/console/services/tools_service.py` (`List`).

## Hành vi mong đợi

Import `app.config` không lỗi; mọi tên `typing` dùng trong module được import ở chính module đó.

## Tái hiện

```bash
git show 427c07f:app/config/server_config.py > /tmp/sc.py
# chạy file với pydantic/pydantic_settings thật (hoặc stub) → NameError: name 'List' is not defined
python -m unittest test.test_typing_imports   # trên develop: FAIL, liệt kê 3 file
```

## Sửa / kiểm chứng

- Thêm `from typing import List` vào `server_config.py`; bổ sung `List`, `Optional` vào import `typing` của `rag_pipeline.py`, `List` cho `tools_service.py`.
- Test hồi quy `test/test_typing_imports.py`: quét AST toàn bộ `app/`, không cần cài dependency. Trên develop: FAIL (3 file). Sau sửa: 2/2 OK.
- Exec `server_config.py` với stub `pydantic`: bản develop `NameError`, bản sửa OK.
- Chưa chạy: bộ test đầy đủ và khởi động service thật (container cloud chưa cài `requirements.txt`).
