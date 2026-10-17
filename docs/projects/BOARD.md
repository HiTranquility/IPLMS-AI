# 📋 BOARD — IPLMS-AI: việc chưa làm, ai nhận, tới đâu

> **Đích:** `docs/projects/BOARD.md` — *một file của repo này, không theo tháng, không có mã* · **Mẫu:** [board-template](../templates/board-template.md)
> Bảng trả lời **ai làm gì, hạn bao giờ, đang tới đâu**. Cách làm và bằng chứng nằm trong hồ sơ được trỏ tới, không nằm ở đây.

## 📌 Meta

| | |
|---|---|
| **Người giữ bảng** | Chủ đồ án |
| **Cập nhật lần cuối** | 2026-10-17 |

## 📏 Luật dùng bảng

1. **[NEVER] viết nội dung vào bảng.** Mỗi việc đúng một dòng. Cần hơn một dòng để giải thích → tạo hồ sơ trong repo này (issue / bug / suggestion) trước, rồi ghi vào cột **Hồ sơ**. Việc vặt thì để `—`.
2. **Việc bắt nguồn từ repo gốc** (IDEA, PROB, bug hay ISSUE xuyên module): ghi mã kèm tên repo, ví dụ `IPLMS IDEA-010`, không dùng link tương đối (repo con clone riêng thì link gãy). Người nhận **không có quyền repo gốc** → mở ISSUE/bug trong repo này, mô tả đủ để làm mà không cần đọc gốc, ghi `Bắt nguồn từ: IPLMS …`, rồi trỏ dòng bảng vào hồ sơ đó.
3. **Việc chạm nhiều repo:** mỗi repo có phần việc thì có một dòng riêng trong bảng của mình, mô tả đúng phần của repo đó.
4. **Nhận việc** = chuyển dòng sang 🚧, điền **Người nhận** + **Hạn**. Xong = chuyển xuống ✅ kèm ngày; trạng thái chi tiết vẫn cập nhật trong hồ sơ.
5. Mục ✅ dọn mỗi đầu tháng — git đã giữ lịch sử.
6. Ưu tiên (lúc lập bảng 2026-10-04 do AI đề xuất từ mức tác động trong hồ sơ — người giữ bảng sửa lại khi giao): 🔴 hỏng luồng chính / bảo mật / mất dữ liệu · 🟠 sai nhưng có đường vòng, hoặc kiểm thử còn treo · 🟢 dọn dẹp, vận hành nhỏ.

## 🙋 Cần người nhận

| Việc | Hồ sơ | Ưu tiên | Ghi chú |
|---|---|---|---|
| Review trước tích hợp: Docker context và lọc dữ liệu build | [bug-003](bugs/bug-003-docker-context-khong-dong-bo/bug.md) | 🔴 | Chỉ phát hiện trên khoa-develop9a1aafd, chưa merge |
| Review trước tích hợp: Launcher REST/gRPC và báo lỗi dependency | [bug-004](bugs/bug-004-launcher-dev-dung-grpc/bug.md) | 🔴 | Chỉ phát hiện trên khoa-develop9a1aafd, chưa merge |
| Review trước tích hợp: Hiệu chỉnh biển số mất ký tự | [bug-005](bugs/bug-005-plate-correction-mat-ky-tu/bug.md) | 🔴 | Chỉ phát hiện trên khoa-develop9a1aafd, chưa merge |
| Review trước tích hợp: Prior loại xe không phải observation | [bug-006](bugs/bug-006-vehicle-prior-gia-lam-observation/bug.md) | 🔴 | Chỉ phát hiện trên khoa-develop9a1aafd, chưa merge |
| Review trước tích hợp: Ingest mapping thời gian sai DTO | [bug-007](bugs/bug-007-ingest-response-sai-duration/bug.md) | 🔴 | Chỉ phát hiện trên khoa-develop9a1aafd, chưa merge |
| Review trước tích hợp: Dashboard render dữ liệu bằng HTML | [bug-008](bugs/bug-008-dashboard-render-html-khong-escape/bug.md) | 🔴 | Chỉ phát hiện trên khoa-develop9a1aafd, chưa merge |
| Đánh giá & calibration phân bố confidence ANPR theo camera | IPLMS PROB-045 | 🟢 | Chuẩn bị dữ liệu sau khi materialize xong |

## 🚧 Đang làm

| Việc | Hồ sơ | Người nhận | Hạn | Tới đâu |
|---|---|---|---|---|
| Làm nốt 1.3 `materialize_dataset` (tải theo manifest + sha256) | IPLMS ISSUE-013 | Khoa | 2026-10-16 | Đang viết CLI & loader từ private storage |
| Restart container `ai` để đường gRPC nạp code mới, rồi verify ANPR | IPLMS bug-006 | Khoa | 2026-10-14 | REST đã verify; chuẩn bị đo gRPC & warmup |
| Đo ANPR trên test-golden snapshot & đối chiếu xe chống tráo | IPLMS ISSUE-010 | Khoa | 2026-10-17 | Chuẩn bị test suite & dữ liệu snapshot |
| AI Console nội bộ: DB riêng, 7 vai trò, đăng nhập Google + TOTP, `ai/ui` | IPLMS ISSUE-126 | Claude Code | — | P1a–P6 xong (P6 theo IPLMS ADR-0051); PR #22 + nhánh xếp chồng chờ CI (billing GitHub). Còn: Google OAuth thật, A2 trên stack dev, QR TOTP, EN — xem IPLMS ISSUE-126 review-6 |
| Chạy bộ test Knowledge Base với LLM thật (cần `AI_LLM_API_KEY`) | IPLMS ISSUE-009 | Dương | 2026-10-15 | 299 test unit/mock đã pass; chờ key/ollama chạy live |
| LangGraph workflow cho Copilot tranh chấp (Phase 3) | IPLMS ISSUE-005 | Dương | 2026-10-18 | Xong phase 2; đang làm tiếp state interrupt/resume |
| Nạp liệu tri thức RAG — phần AI & hoàn tất E2E | IPLMS ISSUE-004 | Dương | 2026-10-16 | Nhóm 5 code xong; chờ E2E container & nối FE |
| Sửa vi phạm so với AI_CONVENTIONS (bổ sung luật lỗi & test doc) | IPLMS AUDIT-004 | Dương | 2026-10-19 | Đã có báo cáo AUDIT-004; cập nhật doc & gRPC mapping |

## ⏳ Chờ duyệt

| Việc | Hồ sơ | Người làm | Người duyệt |
|---|---|---|---|
| Cổng từ chối RAG (chunk vector tốt nhất < `AI_RAG_MIN_SIMILARITY` → không gọi LLM) + eval Copilot end-to-end + bộ held-out — đổi hành vi M2, nhánh `feature/ISSUE-126-2026-10-copilot-abstention-gate` | IPLMS ISSUE-126 review-7 | Claude Code | Khoa / Dương (M2) |

## ⛔ Bị chặn

| Việc | Hồ sơ | Chặn bởi |
|---|---|---|
| Forecast từ backtest tới phục vụ | IPLMS ISSUE-014 | chưa có export phiên đỗ thật đủ dài + lịch sử capacity (dữ liệu từ analytic) |

## ✅ Xong gần đây *(dọn đầu tháng)*

| Việc | Hồ sơ | Người làm | Ngày |
|---|---|---|---|
| Gộp `khoa-develop` (5f24a1f) vào nhánh console, giữ bản develop khi xung đột; bug-011 hết do ADR-0050 bỏ `/api/copilot/ask` | [bug-011](bugs/bug-011-copilot-ask-nhan-api-key-tu-client-va-tra-loi-gia-khi-llm-loi/bug.md) · IPLMS ISSUE-126 | Claude Code | 2026-10-17 |
| Lỗi model không tồn tại bị nuốt thành "AI service unreachable" | IPLMS bug-014 | Dương | 2026-10-13 |
| Sửa 4 lỗi sai im lặng (grader tiền, occupancy 0%, seasonal baseline, phân loại xe) + nâng ANPR/keyword/Forecast | bug-001 · IPLMS PROB-045 | Claude | 2026-10-06 |
