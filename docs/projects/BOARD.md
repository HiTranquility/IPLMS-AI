# 📋 BOARD — IPLMS-AI: việc chưa làm, ai nhận, tới đâu

> **Đích:** `docs/projects/BOARD.md` — *một file của repo này, không theo tháng, không có mã* · **Mẫu:** [board-template](../templates/board-template.md)
> Bảng trả lời **ai làm gì, hạn bao giờ, đang tới đâu**. Cách làm và bằng chứng nằm trong hồ sơ được trỏ tới, không nằm ở đây.

## 📌 Meta

| | |
|---|---|
| **Người giữ bảng** | Chủ đồ án |
| **Cập nhật lần cuối** | 2026-10-19 |
| **Người cập nhật** | Codex — bổ sung dự trù theo lựa chọn B của chủ dự án |

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
| Đo weights ứng viên chưa nạp: nạp theo `artifact_key` trong process đo riêng (module M4) | IPLMS ISSUE-126 phase-6 6.12 | 🟢 | M4 chưa có người |
| Kiểm `review-7.md` + `app/script/eval_copilot_e2e.py` bị sửa trên đĩa sau commit `e616fee`, trước khi push/merge | IPLMS ISSUE-126 review-7 | 🟠 | Người merge chuỗi PR console |

## 🗓️ Dự kiến theo thành viên — chưa nhận việc

Chủ dự án chọn phương án B ngày 2026-10-19: dự trù theo người, chưa giao hạn tuần. **Dự kiến cho** không có nghĩa người đó đã nhận. Các dòng 🚧 bên dưới giữ nguyên theo lần cập nhật trước; hạn cũ cần thành viên xác nhận lại, không suy ra đã xong hoặc đang trễ thực tế.

Thứ tự 1 → 3 là gợi ý trong từng người, sau khi rà việc đang làm và các review 🔴 ở mục 🙋. Chỉ chuyển một việc sang 🚧 khi người nhận xác nhận, điền hạn và bảo đảm đủ điều kiện; di chuyển dòng, không sao chép. M3/M4 chưa có người xác nhận; không coi Claude Code là một thành viên mới của nhóm.

| Dự kiến cho | Thứ tự | Việc | Hồ sơ | Ưu tiên | Bắt đầu khi | Đầu ra để duyệt |
|---|---|---|---|---|---|---|
| Khoa | 1 | Duyệt phần M2 của cổng từ chối Copilot sau đợt code console | IPLMS ISSUE-126 review-7 OPEN-01; BOARD ✅ ngày 2026-10-18 | 🟠 | Chốt revision cần duyệt với Dương; dành được thời gian sau việc M2 đang nhận | Nhận xét chấp nhận/cần sửa, ghi rõ model, ngưỡng và rủi ro câu có similarity cao; chưa tự thay ngưỡng |
| Khoa | 2 | Kiểm và sửa thứ tự chọn proto của `compile_proto.py` nếu còn lệch | IPLMS ISSUE-126 review-6 BUG-06 | 🟢 | Tái hiện trên revision tích hợp; xác nhận nguồn proto và dành được thời gian sau việc M2 | Fixture lệch phiên bản không còn sinh stub thiếu RPC; kiểm đồng bộ caller; nếu đã sửa thì ghi bằng chứng thay vì sửa lại |
| Khoa | 3 | Đánh giá & calibration phân bố confidence ANPR theo camera | IPLMS PROB-045 | 🟢 | `materialize_dataset` và test-golden được xác minh, có tập theo camera đủ dùng | Báo cáo phân bố/sai số theo camera và đề xuất ngưỡng; chưa áp ngưỡng khi chưa duyệt |
| Dương | 1 | Mở rộng bộ held-out Copilot và rà nhãn độc lập | IPLMS ISSUE-126 review-7 S3 | 🟠 | Xong lượt test KB đang nhận; thống nhất nhãn với Khoa và có người viết câu độc lập | ≥ 30 câu held-out có nhãn/nguồn; tách bộ chọn ngưỡng khỏi bộ đánh giá; ghi kết quả khi môi trường local sẵn sàng |
| Dương | 2 | Rà ca kiểm thử restart/resume và duyệt sai cho workflow tranh chấp | [ai ISSUE-001](issues/09-2026/ISSUE-001-langgraph-dispute-workflow/issue.md) | 🟠 | Đối chiếu test phase 1–2 trước; backend xác nhận hợp đồng evidence có quyền cho phần tích hợp | Ma trận test và bằng chứng cho restart/resume, thread không hợp lệ, duyệt lặp; chỉ bổ sung ca còn thiếu; không thực thi hoàn tiền |
| Dương | 3 | I-3: soạn kịch bản demo liên vai console bằng `iplms-demo-loop` | IPLMS ISSUE-126; kênh A2 phase-6 6.3 | 🟢 | Có thời gian sau việc RAG/workflow; chỉ chạy demo thật khi A2, tài khoản test và ngưỡng duyệt sẵn sàng | Kịch bản annotator → reviewer → lead → backend áp ngưỡng, mỗi bước có kết quả đúng; phần chưa chạy ghi rõ bị chặn |
| HiTranquility | 1 | I-2: tổ chức security review AI Console trước buổi bảo vệ | IPLMS ISSUE-126; IPLMS ADR-0048, ADR-0051 | 🟠 | Xác định revision cần review; có tài khoản test và môi trường local cô lập | Checklist đăng nhập/phiên/quyền và PII ảnh cắt, bằng chứng từ chối sai quyền; tách người viết phần quyền với người review khi thực hiện |
| HiTranquility | 2 | Chốt người phụ trách M3/M4 và thứ tự phối hợp console | IPLMS ISSUE-126 — bảng chia việc M0–M4 | 🟠 | Xác nhận lịch và năng lực của nhóm; không mặc định người thứ ba là một tài khoản cụ thể | Tên người được xác nhận cho M3/M4, phạm vi file và người duyệt; cập nhật BOARD khi nhận, không tạo owner trùng |
| HiTranquility | 3 | Điều phối gỡ chặn dữ liệu Forecast F0 | IPLMS ISSUE-014 F0; IPLMS PROB-039 | 🟢 | Xác định người cung cấp export/capacity từ analytic; chưa bật model phục vụ | Danh sách dữ liệu còn thiếu, người cung cấp, timezone và lịch sử capacity cần xác nhận; có nguồn đủ điều kiện mới lên lịch backtest |

Lượt này chỉ lập hàng đợi từ hồ sơ hiện có (IPLMS REQ-006 F7 / ISSUE-125 review-1). Không chạy model, tải dữ liệu, gọi LLM hoặc thay đổi quyền. Các dòng này không thay thế việc đang làm ở dưới.

## 🚧 Đang làm

| Việc | Hồ sơ | Người nhận | Hạn | Tới đâu |
|---|---|---|---|---|
| Làm nốt 1.3 `materialize_dataset` (tải theo manifest + sha256) | IPLMS ISSUE-013 | Khoa | 2026-10-16 | Đang viết CLI & loader từ private storage |
| Restart container `ai` để đường gRPC nạp code mới, rồi verify ANPR | IPLMS bug-006 | Khoa | 2026-10-14 | REST đã verify; chuẩn bị đo gRPC & warmup |
| Đo ANPR trên test-golden snapshot & đối chiếu xe chống tráo | IPLMS ISSUE-010 | Khoa | 2026-10-17 | Chuẩn bị test suite & dữ liệu snapshot |
| AI Console nội bộ: DB riêng, 7 vai trò, đăng nhập Google + TOTP, `ai/ui` | IPLMS ISSUE-126 | Claude Code | — | P1a–P6 + EN (`98c2a88`) + cổng từ chối RAG (`e616fee`) đã code; PR #22, #23 + nhánh xếp chồng chờ CI. Việc còn lại đã tách thành dòng riêng ngày 2026-10-18 |
| Chạy bộ test Knowledge Base với LLM thật (cần `AI_LLM_API_KEY`) | IPLMS ISSUE-009 | Dương | 2026-10-15 | 299 test unit/mock đã pass; chờ key/ollama chạy live |
| LangGraph workflow cho Copilot tranh chấp (Phase 3) | [ai ISSUE-001](issues/09-2026/ISSUE-001-langgraph-dispute-workflow/issue.md) (IPLMS ISSUE-005) | Dương | 2026-10-18 | Xong phase 2; đang làm tiếp state interrupt/resume |
| Nạp liệu tri thức RAG — phần AI & hoàn tất E2E | IPLMS ISSUE-004 | Dương | 2026-10-16 | Nhóm 5 code xong; chờ E2E container & nối FE |
| Sửa vi phạm so với AI_CONVENTIONS (bổ sung luật lỗi & test doc) | IPLMS AUDIT-004 | Dương | 2026-10-19 | Đã có báo cáo AUDIT-004; cập nhật doc & gRPC mapping |
| Đưa Postgres 16 + pgvector vào job CI Python để test DB thật chạy mỗi PR | IPLMS ISSUE-126 review-6 S3 | Dương | — | Mới giao 2026-10-18 |
| Code `khoa-develop` chưa nối vào pipeline develop: lọc thẻ `<think>` trong `llm_factory`, nối hoặc bỏ `guardrail_manager`/`prompt_manager`/`ai_logger`/`llama_server_manager`, viết lại 3 test không gọi mạng | IPLMS ISSUE-126 review-6 BUG-05 · commit `ff479f9` | Khoa | — | Mới giao 2026-10-18 |
| Xác nhận cột "đã kiểm/sửa" mục 3b `AI_USAGE.md` cho phần mình nhận (đề Final §5.3, thiếu là −10%) | IPLMS ISSUE-126 phase-6 6.6 | Chủ module M1–M4 | — | Mới giao 2026-10-18 |
| Siết quyền user DB `ai_console` của process inference: chỉ bảng A2 + `accept_policy` | IPLMS ADR-0051 §Hệ quả | HiTranquility | — | Mới giao 2026-10-18 |

## ⏳ Chờ duyệt

| Việc | Hồ sơ | Người làm | Người duyệt |
|---|---|---|---|
| *(trống)* | | | |

## ⛔ Bị chặn

| Việc | Hồ sơ | Chặn bởi |
|---|---|---|
| Forecast từ backtest tới phục vụ | IPLMS ISSUE-014 | chưa có export phiên đỗ thật đủ dài + lịch sử capacity (dữ liệu từ analytic) |
| Merge chuỗi PR AI Console (ai#22, #23 → backend#24 → frontend#20 → gốc + bump gitlink → nhánh xếp chồng) | IPLMS ISSUE-126 review-6 AI-1/AI-2 | GitHub Actions bị từ chối do billing tài khoản |
| Đăng nhập Google thật cho console | IPLMS ISSUE-126 phase-6 6.2 | chủ đồ án tạo OAuth client trên GCP |
| Chạy kênh A2 end-to-end trên stack dev (M4) | IPLMS ISSUE-126 phase-6 6.3 | chủ đồ án duyệt chạy migration `1803000000000` + bật `VISION_CONSOLE_EXPORT_*` trên stack dùng chung |
| Mã QR TOTP ở trang đăng nhập console | IPLMS ISSUE-126 review-6 OPEN-03 | chủ đồ án duyệt cài `segno==1.6.6` |

## ✅ Xong gần đây *(dọn đầu tháng)*

| Việc | Hồ sơ | Người làm | Ngày |
|---|---|---|---|
| Cổng từ chối Copilot (chunk vector tốt nhất < `AI_RAG_MIN_SIMILARITY` → NO_CONTEXT, không gọi LLM) + eval end-to-end + bộ held-out — **merge trước khi Khoa/Dương duyệt** theo quyết định chủ đồ án 2026-10-18; Khoa/Dương cần xem lại sau | IPLMS ISSUE-126 review-7 | Claude Code | 2026-10-18 |
| Gộp `khoa-develop` (5f24a1f) vào nhánh console, giữ bản develop khi xung đột; bug-011 hết do ADR-0050 bỏ `/api/copilot/ask` | [bug-011](bugs/bug-011-copilot-ask-nhan-api-key-tu-client-va-tra-loi-gia-khi-llm-loi/bug.md) · IPLMS ISSUE-126 | Claude Code | 2026-10-17 |
| Lỗi model không tồn tại bị nuốt thành "AI service unreachable" | IPLMS bug-014 | Dương | 2026-10-13 |
| Sửa 4 lỗi sai im lặng (grader tiền, occupancy 0%, seasonal baseline, phân loại xe) + nâng ANPR/keyword/Forecast | bug-001 · IPLMS PROB-045 | Claude | 2026-10-06 |
