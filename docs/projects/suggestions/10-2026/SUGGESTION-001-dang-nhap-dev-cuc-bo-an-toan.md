# 🌱 SUGGESTION-001: Đăng nhập dev/demo theo vai, cục bộ và an toàn, thay cho `dev-session`

> **Đích:** `docs/projects/suggestions/10-2026/SUGGESTION-001-dang-nhap-dev-cuc-bo-an-toan.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🔄 REVIEWING |
| **Ngày** | 2026-10-23 |
| **Người đề xuất** | Claude Code (rà UI theo yêu cầu chủ dự án, [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md)) |
| **Techlead duyệt** | @HiTranquility — ⏳ chờ |
| **Làm trước khi duyệt?** | Không: chạm xác thực, thuộc diện phải chờ duyệt theo IPLMS ADR-0056 |
| **Phạm vi** | `ai/` (console auth và UI đăng nhập) |

## Đề xuất

Gỡ `/auth/dev-session` ([bug-015](../../bugs/bug-015-dev-session-cua-hau-dang-nhap/bug.md)) và thay bằng một lệnh CLI cục bộ:

```bash
python -m app.script.console_dev_login --role ai_annotator   # in ra URL dùng một lần, hạn 5 phút
```

- Chỉ chạy khi `AI_CONSOLE_DEV_LOGIN=1` và `AI_ENV != production`. Image production không có module này, hoặc module tự từ chối chạy.
- Mỗi vai có một thành viên test `<vai>@test.local` được seed sẵn, ghi audit `auth.dev_login`. Token sinh ngẫu nhiên và chỉ dùng một lần. Trang đăng nhập hiện dải cảnh báo "DEV LOGIN" khi cờ đang bật.

## Vấn đề nó giải quyết

Demo liên vai I-3 (Dương) và review UI (Phát) cần vào được console theo từng vai mà không cần Google OAuth hay TOTP thật. Hôm nay chỉ có cửa hậu "Full 7 Roles", nên không demo được ca "vai thiếu quyền bị từ chối".

## Phạm vi

- Trong: route và CLI dev, seed thành viên test, cảnh báo trên UI, test bảo đảm route trả 404 khi tắt cờ.
- Ngoài: đổi luồng Google + TOTP thật.

## Bằng chứng / tham khảo

- `app/api/rest/routes/console_auth_controller.py:138-142`, `ui/src/pages/Auth/LoginPage.tsx:108-113`.
- Lượt rà ngày 2026-10-23 phải dựng API giả mới xem được UI theo vai ([mock](../../issues/10-2026/ISSUE-004-ai-console-ui-review/evidence/mock_console_api.py)).

## Bước tiếp theo

Techlead duyệt, rồi mở ISSUE riêng. Việc này đụng auth nên cần review bảo mật độc lập theo I-2.
