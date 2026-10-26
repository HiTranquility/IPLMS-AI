# 🐛 bug-032: Hồ sơ nộp Final Project lệch với repo (ADR không có file, prompt viết cứng, mật khẩu mặc định trong compose)

> **Đích:** `docs/projects/bugs/bug-032-ho-so-final-project-lech-voi-repo/bug.md` — ngoài cùng chỉ file này · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🆕 New |
| **Người nhận** | |
| **Hạn** | 2026-10-31 |
| **Ưu tiên** | 🔴 |
| **Ngày đóng** | |
| **Người báo** | Claude (rà README theo đề, CHORE-001) |
| **Ngày báo** | 2026-10-26 |
| **Môi trường** | repo (`develop` tại 2026-10-26) |

## 📋 Việc trên BOARD

| Việc | Người nhận | Hạn | Ưu tiên | Trạng thái |
|---|---|---|---|---|
| Gỡ mật khẩu mặc định khỏi `docker-compose.yml` | | 2026-10-31 | 🔴 | 🆕 New |
| Viết 3 ADR thật mà AI_GUIDE đang gọi là ADR-0008/0009/0010, hoặc sửa AI_GUIDE trỏ ADR có thật | | 2026-10-31 | 🟠 | 🆕 New |
| Đưa prompt Copilot ra `data/prompts/` có version | | 2026-10-31 | 🟠 | 🆕 New |

## Hành vi thực tế

1. **Secret trong Git (đề §11: −5% điểm nhóm).** `docker-compose.yml:91` và `:131` đặt giá trị mặc định cho `AI_DB_PASSWORD` dạng `${AI_DB_PASSWORD:-<mật khẩu thật>}`. Thiếu biến thì compose dùng luôn mật khẩu đó, và chuỗi nằm trong lịch sử Git.
2. **ADR không có file (đề §5.2, vấn đáp §10).** `AI_GUIDE.md:41` và `:325–335` khai 3 ADR nộp bài là ADR-0008 (chống bịa), ADR-0009 (VRAM), ADR-0010 (human-in-the-loop). Repo ai chỉ có `docs/projects/adrs/10-2026/0001-…`; ADR-0008/0009/0010 ở repo gốc IPLMS là chuyện khác (bộ skill, mô hình tài liệu, tên audience). Code và hồ sơ cũng trích "ADR-0008" cho cổng NO_CONTEXT: `app/core/copilot/guardrails/guardrail_manager.py:112`, `app/core/copilot/engines/rag_pipeline.py:243`, `app/api/rest/routes/copilot_controller.py:242`, `AI_USAGE.md:126`, commit `d3ae388` và mô tả HiTranquility/IPLMS-AI#82. ADR guardrail có thật là IPLMS ADR-0029.
3. **Prompt chưa quản lý theo file (đề §4.2).** `app/core/copilot/prompts/prompt_manager.py:29` đọc `data/prompts/<tên>_<version>.txt`, nhưng thư mục đó không có trong repo; `SYSTEM_PROMPT` viết cứng ở `app/core/copilot/engines/rag_pipeline.py:21`.

## Hành vi mong đợi

1. Compose không có giá trị mặc định cho mật khẩu; thiếu biến thì dừng với lỗi rõ (`${AI_DB_PASSWORD:?…}`). Mật khẩu cũ coi như đã lộ: đổi ở mọi môi trường đang dùng.
2. Mỗi ADR mà hồ sơ nộp bài nhắc tới mở được thành file; ít nhất một ADR về thiết kế AI.
3. Prompt hệ thống nằm trong file có version, `prompt_version` ghi trong log khớp tên file.

## Tái hiện

```bash
grep -n "AI_DB_PASSWORD:-" docker-compose.yml
ls docs/projects/adrs/*/ ; grep -n "ADR-0008\|ADR-0009\|ADR-0010" AI_GUIDE.md
ls data/prompts
```

## Bằng chứng

Như mục Hành vi thực tế (`file:line`). Giá trị mật khẩu cố ý không chép vào đây.

## Sửa / kiểm chứng

Chưa sửa. Ghi khi rà README ở [CHORE-001](../../chores/10-2026/CHORE-001-monthly-maintenance/issue.md); README đã ghi đúng trạng thái "chưa đủ" cho mục 2 và 3.
