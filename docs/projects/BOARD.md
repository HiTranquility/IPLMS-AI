# 📋 BOARD — IPLMS-AI: việc chưa làm, ai nhận, tới đâu

> **Đích:** `docs/projects/BOARD.md` — *một file của repo này, không theo tháng, không có mã* · **Mẫu:** [board-template](../templates/board-template.md)
> Bảng trả lời **ai làm gì, hạn bao giờ, đang tới đâu**. Cách làm và bằng chứng nằm trong hồ sơ được trỏ tới, không nằm ở đây.

## 📌 Meta

| | |
|---|---|
| **Người giữ bảng** | Chủ đồ án |
| **Cập nhật lần cuối** | 2026-10-22 |
| **Người cập nhật** | HiTranquility — cập nhật siết quyền DB inference ADR-0051, proto order BUG-06, CI Postgres pgvector S3, review bug-003/004/007 |

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
| Review trước tích hợp: Hiệu chỉnh biển số mất ký tự | [bug-005](bugs/bug-005-plate-correction-mat-ky-tu/bug.md) | 🔴 | Chỉ phát hiện trên khoa-develop9a1aafd, chưa merge |
| Review trước tích hợp: Prior loại xe không phải observation | [bug-006](bugs/bug-006-vehicle-prior-gia-lam-observation/bug.md) | 🔴 | Chỉ phát hiện trên khoa-develop9a1aafd, chưa merge |
| Review trước tích hợp: Dashboard render dữ liệu bằng HTML | [bug-008](bugs/bug-008-dashboard-render-html-khong-escape/bug.md) | 🔴 | Chỉ phát hiện trên khoa-develop9a1aafd, chưa merge |
| Console trả SPA 200 cho `/docs`, test `test_console_http` đỏ sẵn | [bug-014](bugs/bug-014-console-docs-tra-spa-thay-vi-404/bug.md) | 🟢 | Chốt 404 cho /docs hay sửa test |
| Đo weights ứng viên chưa nạp: nạp theo `artifact_key` trong process đo riêng (module M4) | IPLMS ISSUE-126 phase-6 6.12 | 🟢 | M4 chưa có người |

## 🗓️ Dự kiến theo thành viên — chưa nhận việc

Chủ dự án chọn B và yêu cầu hoạch định lại ngày 2026-10-19: **HiTranquility phụ trách phần tổng thể/tích hợp**, Khoa/Dương phụ trách phần AI. **Dự kiến cho** chưa có nghĩa đã bắt đầu. Không chia đều số việc; không tự ấn định hạn tuần hoặc suy ra tiến độ thực tế từ hạn cũ.

Thứ tự là gợi ý trong từng người, sau khi rà việc đang làm và review 🔴 ở mục 🙋. HiTranquility thực hiện nối tiếp theo điều kiện, không phải 7 việc đồng thời. Chuyển dòng sang 🚧 khi xác nhận bắt đầu và hạn. M3/M4 vẫn cần chốt người; Claude Code là tác nhân viết code, không thay người tích hợp.

**Làm rõ theo chủ dự án:** demo liên vai là các vai trên UI của IPLMS-AI, do Dương phụ trách. Thao tác giữa `ui/` và phần API/service trong cùng repo IPLMS-AI vẫn thuộc phạm vi AI. Nếu kịch bản cần sửa code ở repo gốc, backend, frontend, analytic hoặc repo khác, ghi điểm chặn và báo chủ dự án để chốt phần tích hợp với HiTranquility; không tự mở rộng demo.

| Người | Phạm vi phụ trách trong kế hoạch này | Bàn giao / phối hợp |
|---|---|---|
| Khoa | ANPR, model và phần M2 Copilot trong `ai/` | Bàn giao kết quả đo, fixture và test AI cho HiTranquility; không tự nhận sửa caller hoặc cấu trúc repo gốc |
| Dương | RAG/KB, workflow, test AI và demo liên vai trên UI IPLMS-AI | Tự kiểm UI/API trong IPLMS-AI; cần sửa code ngoài repo thì báo chủ dự án; HiTranquility lo phần tích hợp được chốt |
| HiTranquility | Repo gốc, liên kết thư mục/module, proto chung, CI/stack, tích hợp backend/frontend/analytic | Chủ trì phần tổng thể; hỗ trợ khi demo AI phát sinh điểm chặn ngoài repo và chủ dự án chốt; không nhận thay demo UI của Dương |

| Dự kiến cho | Thứ tự | Việc | Hồ sơ | Ưu tiên | Bắt đầu khi | Đầu ra để duyệt |
|---|---|---|---|---|---|---|
| Khoa | 1 | Duyệt phần M2 của cổng từ chối Copilot sau đợt code console | IPLMS ISSUE-126 review-7 OPEN-01; BOARD ✅ ngày 2026-10-18 | 🟠 | Chốt revision cần duyệt với Dương; dành được thời gian sau việc M2 đang nhận | Nhận xét chấp nhận/cần sửa, ghi rõ model, ngưỡng và rủi ro câu có similarity cao; chưa tự thay ngưỡng |
| Khoa | 2 | Đánh giá & calibration phân bố confidence ANPR theo camera — phần AI | IPLMS PROB-045 | 🟢 | `materialize_dataset` và test-golden được xác minh, có tập theo camera đủ dùng | Báo cáo phân bố/sai số theo camera cho HiTranquility đối chiếu tích hợp; chưa áp ngưỡng khi chưa duyệt |
| Khoa | 3 | Kiểm và cải thiện mức bám tài liệu của câu trả lời Copilot khi similarity cao | IPLMS ISSUE-126 review-7 S2, BUG-03 | 🟠 | Chốt revision và tập hồi quy với Dương; dùng LLM local và dữ liệu test được phép | Tái hiện TC-12/TC-17/HO-13, lập kiểm chứng câu trả lời bám nguồn; báo trước/sau và tỷ lệ từ chối nhầm trên câu hợp lệ; đề xuất kiểm đầu ra trước khi đổi hành vi mặc định |
| Khoa | 4 | Benchmark ANPR cold/warm và thời gian từng công đoạn | IPLMS PROB-045 §Baseline và ANPR profiling | 🟠 | Có fixture ảnh AI được phép và model sẵn local; không tải weights mới hoặc restart stack chung | Đo ≥ 3 lượt cold và ≥ 100 lượt warm, p50/p95 và CPU/RAM; tách decode/detect/crop/OCR/classify nơi đo được; lưu phiên bản model, cấu hình và phần cứng để chạy lại |
| Dương | 1 | Mở rộng bộ held-out Copilot và rà nhãn độc lập | IPLMS ISSUE-126 review-7 S3 | 🟠 | Xong lượt test KB đang nhận; thống nhất nhãn với Khoa và có người viết câu độc lập | ≥ 30 câu held-out có nhãn/nguồn; tách bộ chọn ngưỡng khỏi bộ đánh giá; ghi kết quả khi môi trường local sẵn sàng |
| Dương | 2 | Rà test restart/resume và duyệt sai — phần workflow AI | [ai ISSUE-001](issues/09-2026/ISSUE-001-langgraph-dispute-workflow/issue.md) | 🟠 | Đối chiếu test phase 1–2; dùng fixture evidence theo hợp đồng do HiTranquility đối chiếu với backend | Test local cho restart/resume, thread sai, duyệt lặp; chỉ bổ sung ca thiếu; bàn giao phần cần caller backend cho HiTranquility |
| Dương | 3 | I-3: demo liên vai trên UI IPLMS-AI bằng `iplms-demo-loop` | IPLMS ISSUE-126; UI và quyền của AI Console | 🟢 | Có tài khoản test theo vai, dữ liệu test AI và môi trường console local; bước thiếu dữ liệu ghi chặn, không tự cấu hình A2/backend | Kịch bản data engineer, annotator, reviewer, ML engineer, lead và các vai liên quan theo quyền hiện có; kiểm UI, lưu/tải lại và từ chối sai quyền trong AI; cần sửa code ngoài IPLMS-AI thì báo chủ dự án |
| Dương | 4 | Bổ sung test hồi quy quyền 7 vai Console trên UI/API | IPLMS ISSUE-126; `app/core/console/engines/access_policy.py` | 🟠 | Rà test đã có và lập ma trận vai/thao tác; dùng tài khoản hoặc fixture cô lập trong AI | Ma trận đủ 7 vai và quyền hiện có, có test allow/deny cho ca còn thiếu; nút ẩn không thay kiểm API; ghi bằng chứng test tự động, không chỉ checklist demo |
| Dương | 5 | Bổ sung test hồi quy UI khi API lỗi, timeout hoặc phiên hết hạn | IPLMS ISSUE-126; `ui/README.md` và test UI hiện có | 🟠 | Đối chiếu test đã có; mô phỏng lỗi trong test local của `ai/ui`, không phá môi trường chung | Phủ ca còn thiếu cho 401/403/500/timeout tại màn hình liên quan; không báo lưu thành công giả, xử lý retry/đăng nhập theo luồng hiện có; chạy lại suite UI và ghi kết quả |
| HiTranquility | 2 | Restart container `ai` trên stack dev, xác nhận gRPC nạp đúng revision | IPLMS bug-006 | 🟠 | Có cửa sổ thao tác stack dùng chung; xác nhận tác động trước khi restart | Endpoint/version và kiểm gRPC/warmup; Khoa hỗ trợ đo ANPR; chuyển từ dòng Khoa hạn cũ 2026-10-14, chưa coi HiTranquility đã bắt đầu |
| HiTranquility | 4 | Rà revision và tích hợp console/RAG giữa gốc, AI, backend, frontend | IPLMS ISSUE-126 review-7; IPLMS ISSUE-004 | 🟠 | Khoa/Dương bàn giao kết quả AI; kiểm `review-7.md`/`eval_copilot_e2e.py` lệch sau `e616fee`; CI và quyền môi trường sẵn sàng cho phần chạy thật | Bảng revision/gitlink, hợp đồng caller và kết quả E2E RAG; chưa merge/deploy hoặc đổi trạng thái chặn khi chưa có bằng chứng |
| HiTranquility | 5 | I-2: tổ chức security review AI Console trước buổi bảo vệ | IPLMS ISSUE-126; IPLMS ADR-0048, ADR-0051 | 🟠 | Xác định revision; có tài khoản test và môi trường local cô lập | Checklist đăng nhập/phiên/quyền/PII và bằng chứng từ chối sai quyền; người review độc lập với người viết phần quyền |
| HiTranquility | 6 | Chốt người phụ trách M3/M4 và thứ tự phối hợp console | IPLMS ISSUE-126 — bảng chia việc M0–M4 | 🟠 | Xác nhận lịch và năng lực của nhóm; có thể chốt sớm để gỡ phụ thuộc cho các việc trước | Người được xác nhận, phạm vi file/module và người duyệt; không mặc định Khoa/Dương nhận phần ngoài AI |
| HiTranquility | 7 | Điều phối gỡ chặn dữ liệu Forecast F0 với analytic | IPLMS ISSUE-014 F0; IPLMS PROB-039 | 🟢 | Xác định người cung cấp export/capacity; chưa bật model phục vụ | Chốt nguồn dữ liệu, timezone và lịch sử capacity; AI chỉ backtest khi dữ liệu đủ điều kiện |

Kế hoạch mới nhất theo IPLMS REQ-006 F10 / ISSUE-125 review-4: 16 việc dự kiến (Khoa 4, Dương 5, HiTranquility 7), gồm 4 việc kỹ thuật mới thêm. I-3 vẫn thuộc Dương trong IPLMS-AI; các việc tổng thể giữ HiTranquility. Không chạy demo, model, LLM, đổi quyền hoặc thao tác stack trong lượt bổ sung kế hoạch.

## 🚧 Đang làm

| Việc | Hồ sơ | Người nhận | Hạn | Tới đâu |
|---|---|---|---|---|
| Việc vặt tháng 10 — luật ý tưởng giữa chừng + techlead duyệt (IPLMS ADR-0056) | [CHORE-001](chores/10-2026/CHORE-001-monthly-maintenance/issue.md) | @HiTranquility | 2026-10-31 | 🚧 PR chore tháng mở |
| Chặn nạp mẫu demo Vision Lab ở production, sửa nạp lại lỗi 500 / nhãn kẹt bốn mắt | [bug-013](bugs/bug-013-vision-demo-seed-khong-chan-production/bug.md) | @HiTranquility | 2026-10-31 | 🚧 Đã sửa, chờ audit vòng 2 + PR vào develop |
| Định tuyến Root URL và Nâng cấp Copilot Chat Studio 3-Panel | [ISSUE-003](issues/10-2026/ISSUE-003-console-root-routing-copilot-studio/issue.md) | AI Team | 2026-10-31 | 🚧 Đang hoàn thiện UX & sub-components |
| Làm nốt 1.3 `materialize_dataset` (tải theo manifest + sha256) | IPLMS ISSUE-013 | Khoa | 2026-10-16 | Đang viết CLI & loader từ private storage |
| Đo ANPR trên test-golden snapshot — phần AI | IPLMS ISSUE-010 | Khoa | 2026-10-17 | Chuẩn bị test suite & dữ liệu snapshot; phần nối backend/operator và đối chiếu chống tráo do HiTranquility tích hợp |
| AI Console nội bộ: DB riêng, 7 vai trò, đăng nhập Google + TOTP, `ai/ui` | IPLMS ISSUE-126 | Claude Code | — | P1a–P6 + EN (`98c2a88`) + cổng từ chối RAG (`e616fee`) đã code; PR #22, #23 + nhánh xếp chồng chờ CI. Việc còn lại đã tách thành dòng riêng ngày 2026-10-18 |
| Chạy bộ test Knowledge Base với LLM thật (cần `AI_LLM_API_KEY`) | IPLMS ISSUE-009 | Dương | 2026-10-15 | 299 test unit/mock đã pass; chờ key/ollama chạy live |
| LangGraph workflow cho Copilot tranh chấp (Phase 3) | [ai ISSUE-001](issues/09-2026/ISSUE-001-langgraph-dispute-workflow/issue.md) (IPLMS ISSUE-005) | Dương | 2026-10-18 | Xong phase 2; đang làm tiếp state interrupt/resume |
| Nạp liệu tri thức RAG — phần AI | IPLMS ISSUE-004 | Dương | 2026-10-16 | Giữ phần ingest/retrieve và test AI; E2E container, caller backend và nối FE chuyển HiTranquility điều phối |
| Sửa vi phạm so với AI_CONVENTIONS (bổ sung luật lỗi & test doc) | IPLMS AUDIT-004 | Dương | 2026-10-19 | Đã có báo cáo AUDIT-004; cập nhật doc & gRPC mapping |
| Hoàn thiện phần AI của `khoa-develop`: lọc thẻ `<think>`, rà `guardrail_manager`/`prompt_manager`/`ai_logger`/`llama_server_manager`, viết lại 3 test không gọi mạng | IPLMS ISSUE-126 review-6 BUG-05 · commit `ff479f9` | Khoa | — | Giữ sửa/test trong AI; HiTranquility phụ trách nối revision/caller và tích hợp tổng thể; giao gốc 2026-10-18 |
| Xác nhận cột "đã kiểm/sửa" mục 3b `AI_USAGE.md` cho phần mình nhận (đề Final §5.3, thiếu là −10%) | IPLMS ISSUE-126 phase-6 6.6 | Chủ module M1–M4 | — | Mới giao 2026-10-18 |

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
| Siết quyền DB user `ai_console` cho process inference: chỉ bảng A2 + `accept_policy` + verify fail-closed | IPLMS ADR-0051 §Hệ quả | HiTranquility | 2026-10-22 |
| Sửa thứ tự ưu tiên proto gốc (`REPO_ROOT / proto`) trong `compile_proto.py` | IPLMS ISSUE-126 review-6 BUG-06 | HiTranquility | 2026-10-22 |
| Đưa Postgres 16 + pgvector (0.8.6-pg16) vào service job CI Python (`ci.yml`) | IPLMS ISSUE-126 review-6 S3 | HiTranquility | 2026-10-22 |
| Rà soát và kiểm chứng 3 bug tích hợp (bug-003 Docker context, bug-004 launcher REST/gRPC, bug-007 ingest duration_ms) | [bug-003](bugs/bug-003-docker-context-khong-dong-bo/bug.md), [bug-004](bugs/bug-004-launcher-dev-dung-grpc/bug.md), [bug-007](bugs/bug-007-ingest-response-sai-duration/bug.md) | HiTranquility | 2026-10-22 |
| Cổng từ chối Copilot (chunk vector tốt nhất < `AI_RAG_MIN_SIMILARITY` → NO_CONTEXT, không gọi LLM) + eval end-to-end + bộ held-out — **merge trước khi Khoa/Dương duyệt** theo quyết định chủ đồ án 2026-10-18; Khoa/Dương cần xem lại sau | IPLMS ISSUE-126 review-7 | Claude Code | 2026-10-18 |
| Gộp `khoa-develop` (5f24a1f) vào nhánh console, giữ bản develop khi xung đột; bug-011 hết do ADR-0050 bỏ `/api/copilot/ask` | [bug-011](bugs/bug-011-copilot-ask-nhan-api-key-tu-client-va-tra-loi-gia-khi-llm-loi/bug.md) · IPLMS ISSUE-126 | Claude Code | 2026-10-17 |
| Lỗi model không tồn tại bị nuốt thành "AI service unreachable" | IPLMS bug-014 | Dương | 2026-10-13 |
| Sửa 4 lỗi sai im lặng (grader tiền, occupancy 0%, seasonal baseline, phân loại xe) + nâng ANPR/keyword/Forecast | bug-001 · IPLMS PROB-045 | Claude | 2026-10-06 |
