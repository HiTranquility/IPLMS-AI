# Git workflow — IPLMS-AI

Hiệu lực: **2026-10-15**. Bản local của quyết định **ADR-0043** ở umbrella IPLMS; dùng được khi clone riêng. Đây là quy chuẩn tài liệu cho nhánh mới; chưa siết thêm CI và chưa chứng minh toàn bộ CI đã pass.

## Tên nhánh mới

```text
<type>/<record>-<YYYY-MM>-<english-kebab-slug>
```

- `type`: `feature`, `bugfix`, `hotfix`, `chore`, `docs`; slug tiếng Anh, chữ thường, nối bằng dấu gạch ngang.
- `record` giữ đúng mã hồ sơ chính: `ISSUE-NNN`, `bug-NNN`, hoặc `PROB-NNN` nếu namespace sở hữu có loại đó. Không tự tạo mã hay suy ra mã từ số GitHub issue.
- `YYYY-MM` là tháng/năm **tạo gốc của hồ sơ chính**, giữ nguyên khi tiếp tục sang tháng khác. Không dùng tháng làm việc hiện tại. Bug không có thư mục tháng thì đọc metadata ngày tạo; nếu chưa có ngày, xác minh và bổ sung ngày gốc, ghi nguồn ngày rõ trong PR trước khi đặt nhánh, không đoán.
- Mỗi nhánh giải quyết một việc; một issue lớn có thể tách phần việc qua hồ sơ con trước khi tạo nhiều nhánh. Người phụ trách nằm ở assignee/PR, không thêm tên developer vào nhánh.
- Agent mặc định dùng `codex/<record>-<YYYY-MM>-<english-kebab-slug>` khi host yêu cầu prefix `codex/`; PR nêu loại công việc tương ứng. Nhánh Dependabot/release tiếp tục theo workflow riêng hiện hữu.

Ví dụ **giả định**, không cấp mã hồ sơ thật: hồ sơ `ISSUE-013` tạo ngày 2026-09-20 → `feature/ISSUE-013-2026-09-materialize-dataset`; sửa tiếp trong tháng 10 vẫn giữ `2026-09`.

## Hồ sơ, owner và PR

Namespace local có ISSUE và bug theo [bộ mẫu](templates/README.md); PROB xuyên hệ thống thuộc umbrella, không tạo PROB local. Nếu hồ sơ chính thuộc umbrella, ghi rõ owner là IPLMS trong PR.

Mã số độc lập giữa các repo. PR phải ghi **repo sở hữu + mã + đường dẫn hồ sơ**, assignee, phạm vi, bằng chứng kiểm chứng và phần chưa chạy. Việc xuyên repo tham chiếu root issue và local issue nếu đã có; không phát minh local ID hay tháng/năm để đủ khuôn. Chỉ dùng đường dẫn/ID thật; khi clone riêng có thể ghi đường dẫn umbrella dưới dạng văn bản kèm tên repo.

## Base, tích hợp và chuyển tiếp

- `main` và `develop` giữ tên ổn định. Nhánh công việc thường tách từ `develop`, mở PR về `develop`; nhánh không đồng nghĩa môi trường đang triển khai.
- `hotfix` chỉ tách từ `main` khi là sự cố khẩn cấp thực sự, PR về `main` và đồng bộ bản sửa về `develop` bằng PR theo luồng hiện hữu. Merge không cấp quyền deploy; vẫn theo review, CI và quyền vận hành đang áp dụng.
- Giữ nguyên nhánh cũ, gồm `khoa-develop` nếu có; không tự rename, xóa, force-push hay tái cấu trúc lịch sử. Áp dụng dần từ nhánh mới; siết CI là thay đổi riêng cần rà tương thích trước.
- Commit đúng file trong repo này; cập nhật gitlink umbrella là bước riêng.

Tham chiếu local: [AGENTS](../AGENTS.md), [conventions](AI_CONVENTIONS.md).
