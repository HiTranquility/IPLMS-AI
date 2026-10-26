# IPLMS-AI — chỉ dẫn cho coding agents


## 💡 [IDEATION FIRST] Tư Duy Mở & Đề Xuất Trắc Nghiệm (Khi Có Ý Tưởng / Câu Hỏi Mới)

Khi User đưa vào **bất kỳ ý tưởng (Idea), vấn đề mới (Problem), hay câu hỏi kiến trúc mới**:
1. **[Tư duy tự do trước - Unconstrained Brainstorming]:**
   - Không được áp đặt ngay các quy tắc cứng nhắc hay vội vàng từ chối ý tưởng. Hãy cho phép tư duy mở, phân tích đa chiều, tìm ra các giải pháp sáng tạo và tối ưu nhất cho bài toán.
2. **[Đề xuất dạng Multiple-Choice (Trắc nghiệm Lựa chọn)]:**
   - Luôn tổng hợp và đề xuất từ **2 – 4 phương án rõ ràng (A, B, C...)** kèm:
     - Ưu / Nhược điểm & Trade-off của từng lựa chọn.
     - Khuyến nghị (Recommended) phương án phù hợp nhất kèm lý do ngắn gọn.
     - Chờ User phản hồi/lựa chọn trước khi bắt tay vào triển khai.
3. **[Áp quy tắc & Cảnh báo xung đột (Conflict Alert)]:**
   - Sau khi User chọn phương án: tiến hành đối chiếu và áp dụng các tiêu chuẩn/quy ước hiện có của repo (ADR, Conventions, Architecture).
   - Nếu phương án đã chọn có **XUNG ĐỘT (Conflict)** với kiến trúc cũ, ADR đã duyệt, hoặc quy chuẩn hiện tại -> **PHẢI BÁO RÕ XUNG ĐỘT NGAY LẬP TỨC**, nêu rõ nguyên nhân, hệ quả và đề xuất cách xử lý (vd: viết ADR mới thay thế hoặc điều chỉnh phương án) chứ không âm thầm làm hoặc từ chối ngang.

## 🔒 [STRICT PRIVACY] Quy tắc Khóa Chết Chia Sẻ Dữ Liệu & Bảo Mật

> [!CAUTION]
> ĐÂY LÀ ĐIỀU KHOẢN TỐI THƯỢNG. Tất cả AI Agent (Claude, GPT, Gemini, Cursor, v.v.) BẮT BUỘC tuân thủ nghiêm ngặt trong mọi tình huống.

1. **[NEVER] Chia sẻ dữ liệu & Telemetry ra ngoài:**
   - TUYỆT ĐỐI KHÔNG gửi mã nguồn, tài liệu nội bộ, schema DB, hoặc prompt ngữ cảnh ra bất kỳ API/Webhook, dịch vụ phân tích hay máy chủ bên thứ ba nào.
   - Không tự ý thực thi các lệnh mạng (`curl`, `wget`, `Invoke-WebRequest`, python requests) để đẩy dữ liệu ra Internet nếu chưa có yêu cầu trực tiếp từ User.

2. **[NEVER] Đụng vào các thư mục / file tối mật sau:**
   - Thư mục cấm tuyệt đối: `SecretKeys/`, `Thong tin ca nhan/`, các bản backup `*-backup-*`.
   - File cấu hình & Token: `.env`, `.env.*`, `credentials.json`, `token.txt`, `id_rsa*`, `*.pem`, `*.key`, `*.pfx`.
   - Cơ sở dữ liệu nội bộ: `*.db`, `*.sqlite`, `*.sql`, `dump.sql`.
   *(Nếu cần cấu hình mẫu, CHỈ ĐƯỢC PHÉP đọc `.env.example`).*

3. **[MUST] Che giấu dữ liệu (Redaction):**
   - Mọi chuỗi kết nối (Connection String), JWT secret, API key vô tình xuất hiện trên terminal/log PHẢI được che đi ngay lập tức (dạng `***REDACTED***`). Không bao giờ in plain-text ra màn hình chat.

4. **[MUST] Tuân thủ ranh giới Local:**
   - Mọi thao tác build, test, lint, và script phụ trợ chỉ được chạy hoàn toàn trong môi trường Local.
   - Đối với hệ thống có LLM Gateway (như KOS / AIOS), chỉ tương tác qua Router nội bộ theo quy ước, không gọi trực tiếp OpenAI/Anthropic từ code ứng dụng.

`IPLMS-AI` là submodule của repo gốc IPLMS (thư mục `ai/`). Mở từ repo gốc thì dùng bộ skill `iplms-*` và `CLAUDE.md` ở gốc; file này đủ để làm việc khi chỉ clone riêng repo này.

## Stack và quy ước

- Đọc [DESIGN.md](DESIGN.md) trước khi đổi kiến trúc/runtime; cập nhật DESIGN và ngoại lệ cùng thay đổi. README giữ phần vào nhanh, conventions giữ luật code.

- Python: FastAPI + gRPC cho ANPR, Forecast, Copilot/RAG; huấn luyện ở `training/`, notebook ở `notebook/`.
- Quy ước: [AI_CONVENTIONS](docs/standards/AI_CONVENTIONS.md). Hợp đồng ANPR lấy từ tài liệu này, proto và code; skill `anpr-pipeline` ở repo gốc là bản cũ viết cho C#.
- Mở 1–2 file cùng loại trong cùng thư mục và theo đúng cách đang làm trước khi viết mới.
- Tính năng gọi LLM theo [ADR-0029](../docs/projects/adrs/10-2026/0029-nguyen-tac-guardrail-llm.md) ở repo gốc: LLM không cầm quyền, đầu vào độc mặc định, đầu ra qua kiểm tất định (`app/core/copilot/engines/output_guard.py`), đổi prompt/guard phải chạy lại bộ tấn công.

## Kiểm chứng

- Test dùng `unittest`: `python -m unittest test.<tên_module>` cho file bị ảnh hưởng.
- Đổi field gRPC: chạy `proto/check_proto_sync.py` ở repo gốc và kiểm caller NestJS.
- Không tải/ghi đè checkpoint hay dữ liệu trong `model/`, `data/` khi chưa được giao.
- Build pass không thay cho kiểm hành vi. Báo rõ phần đã chạy, bị chặn và chưa chạy.

## Tài liệu

Hồ sơ riêng của repo ở `docs/`: mọi hồ sơ nằm dưới `projects/` — `suggestions/` (SUGGESTION-NNN), `usecases/` (UC: đặc tả cho dev, bảng + sequence), `adrs/`, `issues/`, `bugs/`, `qas/` — theo [bộ mẫu tối thiểu](docs/templates/README.md). Việc xuyên repo (IDEA/PROB/ADR hệ thống, REQ) ghi ở `docs/` của repo gốc IPLMS và link hai chiều; không đổi SUGGESTION ở đây thành IDEA.

## Git và an toàn

- **Một hồ sơ một nhánh:** bắt tay làm ISSUE/bug (chuyển 🚧) thì tách đúng một nhánh từ `develop` mới nhất, tên theo [GIT_WORKFLOW](docs/standards/GIT_WORKFLOW.md) (mã hồ sơ + tháng tạo); tree đang có phiên khác thì dùng worktree `.worktrees/<nhánh>`. Việc xuyên repo dùng cùng tên nhánh ở mỗi repo bị chạm. Tách thêm nhánh/worktree/PR cho cùng việc → hỏi trước. Merge xong gỡ worktree, xoá nhánh; nhánh cũ có sẵn giữ tên.
- **BOARD sinh tự động** (IPLMS ADR-0060): đổi trạng thái/người nhận/hạn thì sửa Meta hồ sơ (`Trạng thái`, `Người nhận`, `Hạn`, `Ưu tiên`, `Ngày đóng`) hoặc bảng `## 📋 Việc trên BOARD` của hồ sơ; **[NEVER]** sửa `docs/projects/BOARD.md` trong nhánh việc — CI trên `develop` sinh lại (`.github/workflows/generated-docs.yml`), PR chạm file đó bị `script/check_generated.py` chặn. Mọi dòng BOARD có hồ sơ trong repo này; việc của hồ sơ gốc → ISSUE ở đây ghi `Bắt nguồn từ: IPLMS …`. Xem trước: `python -X utf8 script/board_gen.py --stdout`.
- **Ngoại lệ việc vặt:** docs, template, script/CI không đổi hành vi, bump thư viện đã kiểm → gom vào nhánh `chore/CHORE-NNN-YYYY-MM-monthly-maintenance` của tháng (một nhánh mỗi tháng, hồ sơ `docs/projects/chores/MM-YYYY/CHORE-NNN-monthly-maintenance/issue.md`, một PR cuối tháng); code nghiệp vụ, API/schema, sửa bug vẫn một hồ sơ một nhánh (IPLMS ADR-0055).
- **Ý tưởng nảy ra giữa chừng:** ghi SUGGESTION `🔄 REVIEWING` trước (không nhét vào nhánh việc đang làm), báo techlead @HiTranquility qua PR draft/Issue gán reviewer + nhãn `suggestion`; việc nhỏ (không đổi API/schema/proto, không chạm tiền/quyền/PII/bảo mật, một repo, revert được, không cần ADR) được làm trước trên nhánh riêng, việc lớn chờ duyệt; **chỉ merge khi SUGGESTION 🟢 ACCEPTED có tên techlead và PR được techlead approve** (IPLMS ADR-0059).
- **Mã hồ sơ:** ISSUE/bug đánh số liên tục trong repo này, đếm qua **mọi** thư mục tháng (không chỉ tháng hiện tại); tạo hồ sơ xong push nhánh ngay để phiên khác thấy mã. Trong checkout IPLMS: cột *Mã kế tiếp* ở `docs/projects/issue-registry.md` của gốc.
- Chỉ stage đúng file mình sửa; [NEVER] `git add .` / `git add -A`. Message mô tả thay đổi thật và ghi phần chưa làm/chưa test.
- Commit trong repo này trước; cập nhật gitlink ở repo gốc là bước riêng khi thuộc phạm vi.
- Hỏi người dùng trước khi cài package mới, chạy lệnh ghi dữ liệu dùng chung hoặc deploy.
