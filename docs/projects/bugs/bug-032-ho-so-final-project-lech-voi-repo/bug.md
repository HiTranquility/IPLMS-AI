# 🐛 bug-032: Hồ sơ nộp Final Project lệch với repo (ADR không có file, prompt viết cứng, mật khẩu mặc định trong compose)

> **Đích:** `docs/projects/bugs/bug-032-ho-so-final-project-lech-voi-repo/bug.md` — ngoài cùng chỉ file này · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed — chờ PR |
| **Người nhận** | HiTranquility |
| **Hạn** | 2026-10-31 |
| **Ưu tiên** | 🔴 |
| **Ngày đóng** | |
| **Người báo** | Claude (rà README theo đề, CHORE-001) |
| **Ngày báo** | 2026-10-26 |
| **Môi trường** | repo (`develop` tại 2026-10-26) |

## 📋 Việc trên BOARD

| Việc | Người nhận | Hạn | Ưu tiên | Trạng thái |
|---|---|---|---|---|
| Gỡ mật khẩu mặc định khỏi `docker-compose.yml` | HiTranquility | 2026-10-31 | 🔴 | ✅ Fixed — chờ PR |
| Viết 3 ADR thật mà AI_GUIDE đang gọi là ADR-0008/0009/0010, hoặc sửa AI_GUIDE trỏ ADR có thật | HiTranquility | 2026-10-31 | 🟠 | ✅ Fixed — chờ PR |
| Đưa prompt Copilot ra `data/prompts/` có version | HiTranquility | 2026-10-31 | 🟠 | ✅ Fixed — chờ PR |

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

Ghi khi rà README ở [CHORE-001](../../chores/10-2026/CHORE-001-monthly-maintenance/issue.md). Sửa trên nhánh `bugfix/bug-032-2026-10-ho-so-final-project-lech-voi-repo` (2026-10-26).

**1. Secret.** `docker-compose.yml:91,133` đổi sang `${AI_DB_PASSWORD:?…}`. Rà thêm thấy `docker/database-vector/init/11-ai-inference-role.sh:14` cũng có mật khẩu mặc định thật cho `AI_INFERENCE_DB_PASSWORD`, và compose không truyền biến này vào container nên giá trị mặc định luôn được dùng: đổi sang `:?`, compose truyền `AI_INFERENCE_DB_PASSWORD` (`docker-compose.yml:96`). `docker-compose.{build,develop,production}.yml` không có mật khẩu. Hai mật khẩu cũ vẫn nằm trong lịch sử Git: **phải đổi ở mọi môi trường**; làm sạch lịch sử (rewrite + force-push) là quyết định của người dùng, chưa làm.

**2. ADR (chọn phương án A).** Viết [ai ADR-0002](../../adrs/10-2026/0002-tu-choi-khi-thieu-ngu-canh.md) (chống bịa, thay "ADR-0008"), [ai ADR-0003](../../adrs/10-2026/0003-nguoi-duyet-truoc-khi-xu-ly-tranh-chap.md) (người duyệt tranh chấp, thay "ADR-0010"), [ai ADR-0004](../../adrs/10-2026/0004-llama-server-mot-slot-vua-vram-4gb.md) (VRAM, thay "ADR-0009"). Đổi mọi trích dẫn trong `AI_GUIDE.md`, `AI_USAGE.md`, code (`guardrail_manager.py`, `rag_pipeline.py`, `copilot_controller.py`, `embedding_client.py`, `seed_console_demo.py`), test và UI (`ui/src/i18n/{vi,en}.ts`, `DisputeSimulator.tsx`). Cổng an toàn Forecast trên UI không có ADR nào: bỏ số, giữ tên nguyên tắc. Hồ sơ cũ (bug-018, ISSUE-003) giữ nguyên làm lịch sử. Số đo VRAM/độ trễ trong AI_GUIDE §6 chưa đo lại; ADR-0004 ghi rõ.

**3. Prompt.** Thêm `data/prompts/copilot_rag_system_v2.txt` (nội dung đúng bằng `SYSTEM_PROMPT` cũ), mở `.gitignore`. `rag_pipeline.py` nạp qua `prompt_manager`; `PROMPT_VERSION` = `copilot_rag_system_v2#<hash 8>` và dùng cho cả các nhánh từ chối (trước ghi `v2` trần). Sửa `AI_GUIDE.md` §4.2/§8.2 (không có file v1; sửa prompt cần khởi động lại).

**Kiểm chứng**
- `docker compose --env-file <không có AI_DB_PASSWORD> config` (cả 3 tổ hợp file) → dừng với "required variable AI_DB_PASSWORD is missing a value"; có biến thì qua bước interpolate.
- `11-ai-inference-role.sh`: có `AI_CONSOLE_DB_PASSWORD` mà thiếu `AI_INFERENCE_DB_PASSWORD` → exit 1, báo lỗi; không có console → exit 0 như cũ.
- Image `iplms-ai:latest`: `compile_proto.py` rồi `python -m unittest discover -s test -t .` → 575 test OK (34 skip), có test mới `test_system_prompt_loaded_from_versioned_file`.
- `python -m app.script.redteam_copilot -n 5` với Ollama `qwen2.5:3b` local → `passed: true`: câu thường đúng 15/15, 0 lộ ở 4 kiểu tấn công, tài liệu độc bị bắt lúc nạp.
- `ui`: `tsc --noEmit` sạch, `vitest run` 94/94.

**Còn lại:** `/.dockerignore` ở repo gốc IPLMS chỉ mở `ai/data/knowledge/*.json`; image build local từ gốc sẽ thiếu `data/prompts/` và dùng prompt dự phòng (log ghi `v1_fallback`). Image CI (`.github/workflows/image.yml`) không bị vì không có `.dockerignore` gốc. Sửa ở PR riêng của repo gốc.
