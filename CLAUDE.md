# CLAUDE.md — IPLMS-AI


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

## 🛑 [STRICT WORKTREE & ENV HYGIENE] Quy tắc Quản lý Git Worktree & Môi trường Chạy

1. **[NEVER] Tự ý đẻ thư mục worktree ngoài repo:**
   - TUYỆT ĐỐI CẤM tạo các thư mục dạng `<project>-wt-*` (ví dụ `IPLMS-wt-*`, `SLKG-wt-*`, `AWS-wt-*`...) nằm ngoài thư mục gốc của repository.
   - Khi thực sự cần tách worktree, BẮT BUỘC đặt bên trong `.worktrees/<loại>/<tên-nhánh>` (đã được cấu hình `.gitignore`).

2. **[MUST] Tự động đồng bộ file cấu hình (`.env*`) khi tạo worktree:**
   - Do `.env`, `.env.dev`, `.env.local` nằm trong `.gitignore`, bất kỳ agent hay script nào tạo `git worktree` PHẢI tự động copy hoặc symlink các file `.env*` cần thiết từ thư mục gốc sang worktree mới ngay lập tức.
   - CẤM để worktree chạy ở trạng thái thiếu biến môi trường (tránh lỗi `NOT_CONFIGURED`, mất kết nối DB, OAuth/OIDC, hoặc thiếu API key).

3. **[MUST] Khởi chạy dịch vụ & kiểm thử từ thư mục gốc:**
   - Luôn bật Docker, chạy server (Backend, Frontend, AI, Worker) và test tính năng từ thư mục gốc của dự án, KHÔNG mở các thư mục `-wt-*` làm active workspace chính để chạy ứng dụng.

4. **[MUST] Dọn sạch worktree ngay sau khi hoàn tất (Worktree Lifecycle):**
   - Ngay sau khi task/issue hoàn thành hoặc nhánh đã được merge, agent PHẢI chạy `git worktree remove <path>` và xóa sạch thư mục worktree đó. Tuyệt đối không để lại thư mục worktree mồ côi (orphan worktree).

Chỉ dẫn chung cho mọi coding agent nằm ở `AGENTS.md`; file này chỉ nạp lại để Claude và Codex đọc cùng một nguồn. Thêm luật mới vào `AGENTS.md`, không chép sang đây.

@AGENTS.md
