# 📋 BOARD — IPLMS-AI: việc chưa làm, ai nhận, tới đâu

> **Sinh tự động** bởi `python -X utf8 script/board_gen.py` từ Meta hồ sơ — **[NEVER] sửa tay** (IPLMS ADR-0060). Đổi trạng thái, người nhận, hạn, ưu tiên: sửa Meta của hồ sơ (`Trạng thái`, `Người nhận`, `Hạn`, `Ưu tiên`, `Ngày đóng`) hoặc bảng `## 📋 Việc trên BOARD` trong hồ sơ. CI sinh lại bảng sau mỗi lần merge vào `develop`; xem trước ở máy: `python -X utf8 script/board_gen.py --stdout`.
> Ưu tiên: 🔴 hỏng luồng chính / bảo mật / mất dữ liệu · 🟠 sai nhưng có đường vòng, hoặc kiểm thử còn treo · 🟡 nên làm · 🟢 dọn dẹp, vận hành nhỏ.

## 🙋 Cần người nhận

| Việc | Hồ sơ | Ưu tiên | Trạng thái |
|---|---|---|---|
| Review trước tích hợp: Hiệu chỉnh biển số mất ký tự | [bug-005](bugs/bug-005-plate-correction-mat-ky-tu/bug.md) | 🔴 | Chỉ phát hiện trên khoa-develop9a1aafd, chưa merge |
| Review trước tích hợp: Prior loại xe không phải observation | [bug-006](bugs/bug-006-vehicle-prior-gia-lam-observation/bug.md) | 🔴 | Chỉ phát hiện trên khoa-develop9a1aafd, chưa merge |
| Review trước tích hợp: Dashboard render dữ liệu bằng HTML | [bug-008](bugs/bug-008-dashboard-render-html-khong-escape/bug.md) | 🔴 | Chỉ phát hiện trên khoa-develop9a1aafd, chưa merge |
| Đo weights ứng viên chưa nạp: nạp theo `artifact_key` trong process đo riêng (module M4) | IPLMS ISSUE-126 phase-6 6.12 | 🟢 | M4 chưa có người |
| Gỡ cửa hậu `/auth/dev-session` + nút "Truy cập nhanh", đính chính AUDIT-005 | [bug-015](bugs/bug-015-dev-session-cua-hau-dang-nhap/bug.md) | 🔴 | Đề xuất HiTranquility (auth M1), chờ chủ dự án chốt (ISSUE-004 OPEN-04); đã sửa trên nhánh `bugfix/bug-015-2026-10-console-auth-hardening`, còn xoá phiên cũ + đính chính AUDIT-005 |
| Bỏ mật khẩu mặc định trong `harden_console_db.py`, đổi mật khẩu role `ai_console` | [bug-016](bugs/bug-016-mat-khau-db-console-mac-dinh-trong-code/bug.md) | 🔴 | Đề xuất HiTranquility; đã sửa trên nhánh `bugfix/bug-015-2026-10-console-auth-hardening`, còn đổi mật khẩu ở các môi trường |
| Gỡ mã TOTP cố định `000000`/`123456` vượt MFA và step-up | [bug-026](bugs/bug-026-ma-totp-co-dinh-vuot-xac-thuc/bug.md) | 🔴 | Đã sửa trên nhánh `bugfix/bug-015-2026-10-console-auth-hardening`; còn rà nhật ký phiên từ 2026-10-21 |
| UI: gỡ hoặc gắn nhãn MÔ PHỎNG cho 7 chỗ bịa kết quả, chuyển `fetch` thẳng sang `apiEndpoints` | [bug-018](bugs/bug-018-ui-bia-ket-qua-khi-api-loi/bug.md) | 🔴 | Đã sửa + nối API thật (ANPR, Anti-Fraud, tri thức, chẩn đoán) trên `bugfix/bug-017-2026-10-chat-studio-contract`; còn Dispute thật (Dương, ai ISSUE-001) và Forecast (chưa có model) |
| Chat Studio luôn 422: chốt nhận hay bỏ tham số Playground (Khoa), sửa UI (Phát), test hợp đồng (Dương) | [bug-017](bugs/bug-017-chat-studio-luon-422/bug.md) | 🔴 | OPEN-01 chốt (a) backend nhận tham số; đã sửa trên `bugfix/bug-017-2026-10-chat-studio-contract` |
| UI: escape CSV audit + từ điển mã hành động khớp server | [bug-019](bugs/bug-019-audit-xuat-csv-khong-escape/bug.md), [bug-020](bugs/bug-020-audit-tu-dien-hanh-dong-lech-server/bug.md) | 🟠 | Đã sửa trên `bugfix/bug-019-2026-10-audit-export-and-actions` |
| UI: sửa tràn ngang `/tools` ở 768px + contrast token `--color-faded`/accent hai theme | [bug-024](bugs/bug-024-trang-cong-cu-tran-ngang-o-768px/bug.md), [bug-025](bugs/bug-025-mau-chu-faded-va-accent-duoi-nguong-tuong-phan/bug.md) | 🟠 | Đã sửa trên `bugfix/bug-021-2026-10-console-ui-polish` (66 màn: 0 tràn, 0 dưới AA) |
| UI: bóc i18n còn sót (419 dòng / 47 file) + kiểm tự động | [bug-023](bugs/bug-023-che-do-en-tron-tieng-viet/bug.md) | 🟡 | Đã sửa trên `bugfix/bug-021-2026-10-console-ui-polish` + test chặn chữ viết cứng |
| UI: trục ngày biểu đồ, cờ ảnh khi gán nhãn, hai chú giải ở Vision | [bug-021](bugs/bug-021-bieu-do-xu-huong-cat-nhan-ngay/bug.md), [bug-022](bugs/bug-022-thuoc-tinh-anh-gan-nhan-khong-luu/bug.md) | 🟡 | Đã sửa trên `bugfix/bug-021-2026-10-console-ui-polish`; OPEN-02 chốt lưu cờ vào DB |
| UI: sidebar trên màn hẹp + smoke test browser 7 vai × viewport × theme | [SUGGESTION-003](suggestions/10-2026/SUGGESTION-003-rail-thu-gon-tren-man-hep.md), [SUGGESTION-002](suggestions/10-2026/SUGGESTION-002-mock-api-va-ma-tran-browser-cho-ui.md) | 🟡 | SUGGESTION-003 🟢 ACCEPTED và đã làm ở ISSUE-006; SUGGESTION-002 (smoke test ma trận browser) vẫn chờ techlead |
| Đăng nhập dev theo vai an toàn (gỡ chặn demo I-3) | [SUGGESTION-001](suggestions/10-2026/SUGGESTION-001-dang-nhap-dev-cuc-bo-an-toan.md) | 🟠 | Chờ techlead duyệt; Dương dùng cho demo |
| Lưu cờ ảnh khi gán nhãn để đo ANPR theo điều kiện | [SUGGESTION-004](suggestions/10-2026/SUGGESTION-004-luu-thuoc-tinh-anh-khi-gan-nhan.md) | 🟢 | Đề xuất Khoa xác nhận, UI Phát |
| Ca hồi quy và so A/B prompt trong Copilot Lab | [SUGGESTION-005](suggestions/10-2026/SUGGESTION-005-gom-luot-chat-vao-bo-eval.md) | 🟢 | Đề xuất Khoa + Dương (định dạng ca), UI Phát |

## 🗓️ Đã giao, chưa bắt đầu

| Việc | Hồ sơ | Người nhận | Hạn | Ưu tiên |
|---|---|---|---|---|
| Benchmark ANPR cold/warm và thời gian từng công đoạn | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | Khoa |  | 🟠 |
| Bổ sung test hồi quy UI khi API lỗi, timeout hoặc phiên hết hạn | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | Dương |  | 🟠 |
| Bổ sung test hồi quy quyền 7 vai Console trên UI/API | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | Dương |  | 🟠 |
| Chốt người phụ trách M3/M4 và thứ tự phối hợp console | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | HiTranquility |  | 🟠 |
| Duyệt phần M2 của cổng từ chối Copilot sau đợt code console | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | Khoa |  | 🟠 |
| I-2: tổ chức security review AI Console trước buổi bảo vệ | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | HiTranquility |  | 🟠 |
| Kiểm và cải thiện mức bám tài liệu của câu trả lời Copilot khi similarity cao | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | Khoa |  | 🟠 |
| Nâng cấp toàn bộ phần Vision: model + pipeline ANPR (detector, OCR, hậu xử lý biển số) và Vision La… | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | Dương |  | 🟠 |
| Restart container `ai` trên stack dev, xác nhận gRPC nạp đúng revision | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | HiTranquility |  | 🟠 |
| Rà revision và tích hợp console/RAG giữa gốc, AI, backend, frontend | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | HiTranquility |  | 🟠 |
| Soát PR ISSUE-019: soát lại chéo audit-6 và chạy convention audit cho phần UI của review-2, kiểm UI… | [ISSUE-019](issues/10-2026/ISSUE-019-console-settings-va-don-audit-006/issue.md) | Dương |  | 🟠 |
| Chuyển ứng viên Eval từ `var/eval_candidates.json` vào bảng DB có retention (finding A-37 phần còn … | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | Dương |  | 🟡 |
| Seed demo trung thực: bỏ số tự đặt trong lý do đề xuất ngưỡng (`seed_console_demo.py` mục 4, A-71),… | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | Dương |  | 🟡 |
| Sửa `AI_GUIDE.md:315` và `AI_USAGE.md:34`, `:79`, `:102` cho khớp việc AI không còn tự bật llama-se… | [ISSUE-019](issues/10-2026/ISSUE-019-console-settings-va-don-audit-006/issue.md) | Khoa |  | 🟡 |
| I-3: demo liên vai trên UI IPLMS-AI bằng `iplms-demo-loop` | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | Dương |  | 🟢 |
| Điều phối gỡ chặn dữ liệu Forecast F0 với analytic | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | HiTranquility |  | 🟢 |
| Đánh giá & calibration phân bố confidence ANPR theo camera — phần AI | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | Khoa |  | 🟢 |

## 🚧 Đang làm

| Việc | Hồ sơ | Người nhận | Hạn | Tới đâu |
|---|---|---|---|---|
| Chạy bộ test Knowledge Base với LLM thật (cần `AI_LLM_API_KEY`) | [ISSUE-013](issues/10-2026/ISSUE-013-phan-ai-cua-iplms-issue-009/issue.md) | Dương | 2026-10-15 | 🚧 299 test unit/mock đã pass; chờ key/ollama chạy live |
| Nạp liệu tri thức RAG — phần AI | [ISSUE-012](issues/10-2026/ISSUE-012-phan-ai-cua-iplms-issue-004/issue.md) | Dương | 2026-10-16 | 🚧 Giữ phần ingest/retrieve và test AI; E2E container, caller backend và nối FE chuyển HiTranquility… |
| Làm nốt 1.3 `materialize_dataset` (tải theo manifest + sha256) | [ISSUE-015](issues/10-2026/ISSUE-015-phan-ai-cua-iplms-issue-013/issue.md) | Khoa | 2026-10-16 | 🚧 Đang viết CLI & loader từ private storage |
| Đo ANPR trên test-golden snapshot — phần AI | [ISSUE-014](issues/10-2026/ISSUE-014-phan-ai-cua-iplms-issue-010/issue.md) | Khoa | 2026-10-17 | 🚧 Chuẩn bị test suite & dữ liệu snapshot; phần nối backend/operator và đối chiếu chống tráo do HiTr… |
| LangGraph Workflow Cho Copilot Tranh Chấp | [ISSUE-001](issues/09-2026/ISSUE-001-langgraph-dispute-workflow/issue.md) | Dương | 2026-10-18 | 🚧 In Progress (phase 2 complete) |
| Sửa vi phạm so với AI_CONVENTIONS (bổ sung luật lỗi & test doc) | [ISSUE-011](issues/10-2026/ISSUE-011-phan-ai-cua-iplms-audit-004/issue.md) | Dương | 2026-10-19 | 🚧 Đã có báo cáo AUDIT-004; cập nhật doc & gRPC mapping |
| Việc vặt tháng 10/2026 | [CHORE-001](chores/10-2026/CHORE-001-monthly-maintenance/issue.md) | @HiTranquility | 2026-10-31 | 🚧 In progress |
| Định tuyến trực tiếp Root URL và Nâng cấp Copilot Chat Studio 3-Panel | [ISSUE-003](issues/10-2026/ISSUE-003-console-root-routing-copilot-studio/issue.md) | AI Team | 2026-10-31 | 🚧 In progress |
| Copilot SSE Streaming & Console Telemetry Integration | [ISSUE-002](issues/10-2026/ISSUE-002-copilot-sse-streaming-and-console-telemetry/issue.md) |  |  | 🚧 In progress |
| Củng cố kết nối DB, quản lý tài liệu tri thức, batch upload và tối ưu phân bổ VRAM 4GB cho Console … | [ISSUE-007](issues/10-2026/ISSUE-007-console-tools-and-knowledge-management/issue.md) |  |  | 🚧 IN PROGRESS |
| Mở Rộng Bộ Dữ Liệu Held-Out Copilot RAG Lên ≥ 30 Câu Hỏi-Đáp Độc Lập | [ISSUE-007](issues/10-2026/ISSUE-007-copilot-rag-heldout-dataset/issue.md) |  |  | 🚧 In progress |
| AI Console nội bộ: DB riêng, 7 vai trò, đăng nhập Google + TOTP, `ai/ui` | [ISSUE-017](issues/10-2026/ISSUE-017-phan-ai-cua-iplms-issue-126/issue.md) | Claude Code |  | 🚧 P1a–P6 + EN (`98c2a88`) + cổng từ chối RAG (`e616fee`) đã code; PR #22, #23 + nhánh xếp chồng chờ… |
| Hoàn thiện phần AI của `khoa-develop`: lọc thẻ `<think>`, rà `guardrail_manager`/`prompt_manager`/`… | [ISSUE-017](issues/10-2026/ISSUE-017-phan-ai-cua-iplms-issue-126/issue.md) | Khoa |  | 🚧 Giữ sửa/test trong AI; HiTranquility phụ trách nối revision/caller và tích hợp tổng thể; giao gốc… |
| Xác nhận cột "đã kiểm/sửa" mục 3b `AI_USAGE.md` cho phần mình nhận (đề Final §5.3, thiếu là −10%) | [ISSUE-017](issues/10-2026/ISSUE-017-phan-ai-cua-iplms-issue-126/issue.md) | Chủ module M1–M4 |  | 🚧 Mới giao 2026-10-18 |
| CI unit thiếu runtime dependencies và benchmark fixture bị làm tròn về 0 | [bug-010](bugs/bug-010-ci-fixture-dependencies-va-benchmark-rounding/bug.md) |  |  | 🛠️ Fixing — source/local đã sửa, chờ checkPR / P2 |

## ⏳ Chờ duyệt

| Việc | Hồ sơ | Người nhận | Tới đâu |
|---|---|---|---|
| Hiệu chỉnh biển số cắt mất ký tự nhưng giữ confidence | [bug-005](bugs/bug-005-plate-correction-mat-ky-tu/bug.md) |  | ✅ Fixed trong nhánh tích hợp — chưa merge / P1 |
| Không có model vẫn trả loại xe suy từ biển như nhận dạng ảnh | [bug-006](bugs/bug-006-vehicle-prior-gia-lam-observation/bug.md) |  | ✅ Fixed trong nhánh tích hợp — chưa merge / P1 |
| Dashboard mới render câu hỏi và câu trả lời bằng innerHTML | [bug-008](bugs/bug-008-dashboard-render-html-khong-escape/bug.md) |  | ✅ Fixed trong nhánh tích hợp — chưa merge / P1 |
| Đăng nhập dev/demo theo vai, cục bộ và an toàn, thay cho `dev-session` | [SUGGESTION-001](suggestions/10-2026/SUGGESTION-001-dang-nhap-dev-cuc-bo-an-toan.md) |  | 🔄 REVIEWING |
| Lưu thuộc tính ảnh khi gán nhãn để đo ANPR theo điều kiện ảnh | [SUGGESTION-004](suggestions/10-2026/SUGGESTION-004-luu-thuoc-tinh-anh-khi-gan-nhan.md) |  | 🔄 REVIEWING |
| Đưa lượt chat đã chấm thành ca hồi quy và so A/B phiên bản prompt ngay trong Copilot Lab | [SUGGESTION-005](suggestions/10-2026/SUGGESTION-005-gom-luot-chat-vao-bo-eval.md) |  | 🔄 REVIEWING |
| Nút nạp mẫu demo Vision Lab không chặn production, nạp lại lỗi 500 và nhãn kẹt bốn mắt | [bug-013](bugs/bug-013-vision-demo-seed-khong-chan-production/bug.md) | @HiTranquility | ✅ Fixed — chờ PR (nhánh `bugfix/bug-013-2026-10-vision-demo-seed-guard`) |
| Bổ Sung Test Hồi Quy Ma Trận Quyền 7 Vai Trò AI Console & Chặn API Sai Quyền | [ISSUE-008](issues/10-2026/ISSUE-008-console-access-policy-regression-tests/issue.md) |  | 🟢 Resolved (Chờ merge PR) |
| Bổ Sung Test Hồi Quy UI Khi API Lỗi, Timeout Hoặc Phiên Hết Hạn | [ISSUE-009](issues/10-2026/ISSUE-009-console-ui-error-resilience-tests/issue.md) |  | 🟢 Resolved (Chờ merge PR) |
| Kịch Bản & Kiểm Chứng Tự Động Demo Liên Vai I-3 Trên UI AI Console | [ISSUE-010](issues/10-2026/ISSUE-010-console-cross-role-demo-loop/issue.md) |  | 🟢 Resolved (Chờ merge PR) |
| API giả có hợp đồng và smoke test browser 7 vai × 3 viewport × 2 theme cho `ai/ui` | [SUGGESTION-002](suggestions/10-2026/SUGGESTION-002-mock-api-va-ma-tran-browser-cho-ui.md) |  | 🔄 REVIEWING |
| Generator mới tạo checkpoint ngẫu nhiên vào đường model phục vụ | [bug-009](bugs/bug-009-random-checkpoint-khong-phai-model-da-train/bug.md) |  | ✅ Fixed trong nhánh tích hợp — chưa merge / P2 |
| Test `publish_scope` dùng fixture `validate` cũ, luôn FAIL khi có Postgres thật | [bug-012](bugs/bug-012-test-publish-concurrency-fixture-cu/bug.md) |  | ✅ Fixed — chờ PR / P3 (chỉ test, không đổi code chạy) |

## ⛔ Bị chặn

| Việc | Hồ sơ | Người nhận | Tới đâu |
|---|---|---|---|
| Forecast từ backtest tới phục vụ | [ISSUE-016](issues/10-2026/ISSUE-016-phan-ai-cua-iplms-issue-014/issue.md) |  | ⛔ Bị chặn — chưa có export phiên đỗ thật đủ dài + lịch sử capacity (dữ liệu từ analytic) |
| Chạy kênh A2 end-to-end trên stack dev (M4) | [ISSUE-017](issues/10-2026/ISSUE-017-phan-ai-cua-iplms-issue-126/issue.md) |  | ⛔ Bị chặn — chủ đồ án duyệt chạy migration `1803000000000` + bật `VISION_CONSOLE_EXPORT_*` trên sta… |
| Merge chuỗi PR AI Console (ai#22, #23 → backend#24 → frontend#20 → gốc + bump gitlink → nhánh xếp c… | [ISSUE-017](issues/10-2026/ISSUE-017-phan-ai-cua-iplms-issue-126/issue.md) |  | ⛔ Bị chặn — GitHub Actions bị từ chối do billing tài khoản |
| Mã QR TOTP ở trang đăng nhập console | [ISSUE-017](issues/10-2026/ISSUE-017-phan-ai-cua-iplms-issue-126/issue.md) |  | ⛔ Bị chặn — chủ đồ án duyệt cài `segno==1.6.6` |
| Đăng nhập Google thật cho console | [ISSUE-017](issues/10-2026/ISSUE-017-phan-ai-cua-iplms-issue-126/issue.md) |  | ⛔ Bị chặn — chủ đồ án tạo OAuth client trên GCP |

## ✅ Xong gần đây (20 hồ sơ có Ngày đóng mới nhất)

| Việc | Hồ sơ | Người làm | Ngày |
|---|---|---|---|
| Console trả 404 cho /docs, /redoc, /openapi.json (không lộ qua SPA fallback) | [bug-014](bugs/bug-014-console-docs-tra-spa-thay-vi-404/bug.md) | HiTranquility | 2026-10-25 |
| Gỡ 3 lỗ hổng đăng nhập console: dev-session, mật khẩu DB mặc định, mã TOTP cố định | [bug-015](bugs/bug-015-dev-session-cua-hau-dang-nhap/bug.md), [bug-016](bugs/bug-016-mat-khau-db-console-mac-dinh-trong-code/bug.md), [bug-026](bugs/bug-026-ma-totp-co-dinh-vuot-xac-thuc/bug.md) — #50 | HiTranquility | 2026-10-24 |
| Chat Studio hết 422; UI hết bịa số; nối API thật ANPR, Anti-Fraud, tri thức, chẩn đoán | [bug-017](bugs/bug-017-chat-studio-luon-422/bug.md), [bug-018](bugs/bug-018-ui-bia-ket-qua-khi-api-loi/bug.md) — #51 | HiTranquility | 2026-10-24 |
| CSV audit an toàn, từ điển mã hành động khớp server | [bug-019](bugs/bug-019-audit-xuat-csv-khong-escape/bug.md), [bug-020](bugs/bug-020-audit-tu-dien-hanh-dong-lech-server/bug.md) — #52 | HiTranquility | 2026-10-24 |
| Trục ngày, lưu cờ ảnh gán nhãn, i18n đủ VI/EN, tương phản AA, hết tràn ngang | [bug-021](bugs/bug-021-bieu-do-xu-huong-cat-nhan-ngay/bug.md) … [bug-025](bugs/bug-025-mau-chu-faded-va-accent-duoi-nguong-tuong-phan/bug.md) — #53 | HiTranquility | 2026-10-24 |
| Chỉnh UI console (token, bỏ glow, ngày giờ) · sidebar ngăn kéo màn hẹp + căn hàng form model | [ISSUE-005](issues/10-2026/ISSUE-005-console-ui-polish/issue.md) #54, [ISSUE-006](issues/10-2026/ISSUE-006-console-rail-and-form-align/issue.md) #55 | HiTranquility | 2026-10-24 |
| Rà `ai/ui` bằng REA: 9 bug, 5 suggestion, báo cáo UI/UX + quy chuẩn, gợi ý giao việc | [ISSUE-004](issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) | Claude Code | 2026-10-23 |
| Siết quyền DB user `ai_console` cho process inference: chỉ bảng A2 + `accept_policy` + verify fail-closed | IPLMS ADR-0051 §Hệ quả | HiTranquility | 2026-10-22 |
| Sửa thứ tự ưu tiên proto gốc (`REPO_ROOT / proto`) trong `compile_proto.py` | IPLMS ISSUE-126 review-6 BUG-06 | HiTranquility | 2026-10-22 |
| Đưa Postgres 16 + pgvector (0.8.6-pg16) vào service job CI Python (`ci.yml`) | IPLMS ISSUE-126 review-6 S3 | HiTranquility | 2026-10-22 |
| Rà soát và kiểm chứng 3 bug tích hợp (bug-003 Docker context, bug-004 launcher REST/gRPC, bug-007 ingest duration_ms) | [bug-003](bugs/bug-003-docker-context-khong-dong-bo/bug.md), [bug-004](bugs/bug-004-launcher-dev-dung-grpc/bug.md), [bug-007](bugs/bug-007-ingest-response-sai-duration/bug.md) | HiTranquility | 2026-10-22 |
| Cổng từ chối Copilot (chunk vector tốt nhất < `AI_RAG_MIN_SIMILARITY` → NO_CONTEXT, không gọi LLM) + eval end-to-end + bộ held-out — **merge trước khi Khoa/Dương duyệt** theo quyết định chủ đồ án 2026-10-18; Khoa/Dương cần xem lại sau | IPLMS ISSUE-126 review-7 | Claude Code | 2026-10-18 |
| Gộp `khoa-develop` (5f24a1f) vào nhánh console, giữ bản develop khi xung đột; bug-011 hết do ADR-0050 bỏ `/api/copilot/ask` | [bug-011](bugs/bug-011-copilot-ask-nhan-api-key-tu-client-va-tra-loi-gia-khi-llm-loi/bug.md) · IPLMS ISSUE-126 | Claude Code | 2026-10-17 |
| Lỗi model không tồn tại bị nuốt thành "AI service unreachable" | IPLMS bug-014 | Dương | 2026-10-13 |
| Sửa 4 lỗi sai im lặng (grader tiền, occupancy 0%, seasonal baseline, phân loại xe) + nâng ANPR/keyword/Forecast | bug-001 · IPLMS PROB-045 | Claude | 2026-10-06 |
