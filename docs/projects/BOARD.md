# 📋 BOARD — IPLMS-AI: việc chưa làm, ai nhận, tới đâu

> **Sinh tự động** bởi `python -X utf8 script/board_gen.py` từ Meta hồ sơ — **[NEVER] sửa tay** (IPLMS ADR-0060). Đổi trạng thái, người nhận, hạn, ưu tiên: sửa Meta của hồ sơ (`Trạng thái`, `Người nhận`, `Hạn`, `Ưu tiên`, `Ngày đóng`) hoặc bảng `## 📋 Việc trên BOARD` trong hồ sơ. CI sinh lại bảng sau mỗi lần merge vào `develop`; xem trước ở máy: `python -X utf8 script/board_gen.py --stdout`.
> Ưu tiên: 🔴 hỏng luồng chính / bảo mật / mất dữ liệu · 🟠 sai nhưng có đường vòng, hoặc kiểm thử còn treo · 🟡 nên làm · 🟢 dọn dẹp, vận hành nhỏ.

## 🙋 Cần người nhận

| Việc | Hồ sơ | Ưu tiên | Trạng thái |
|---|---|---|---|
| RAG không có ngữ cảnh vẫn gọi LLM — 2 test đỏ trên `develop` | [bug-047](bugs/bug-047-rag-khong-ngu-canh-van-goi-llm/bug.md) | 🟠 | 🆕 New |
| Guard "ngoài phạm vi" không chuẩn hoá Unicode và dễ lách bằng cách diễn đạt lại | [bug-051](bugs/bug-051-guard-ngoai-pham-vi-khong-chuan-hoa-unicode-va-de-lach-bang-dien-dat-lai/bug.md) | 🟠 | 🆕 New |
| `main` ghim `grpcio-tools==1.84.1` cùng `protobuf==5.29.5`, pip không cài được nên image build hỏng | [bug-054](bugs/bug-054-main-ghim-grpcio-tools-xung-dot-protobuf/bug.md) | 🟠 | 🆕 New |
| Copilot báo "chưa tìm thấy thông tin" khi LLM/embedding sập, không báo lỗi AI | [bug-052](bugs/bug-052-copilot-bao-khong-co-thong-tin-khi-llm-hoac-embedding-sap/bug.md) | 🟡 | 🆕 New |
| Đo weights ứng viên chưa nạp: nạp theo `artifact_key` trong process đo riêng (module M4) | [ISSUE-017](issues/10-2026/ISSUE-017-phan-ai-cua-iplms-issue-126/issue.md) | 🟢 | 🆕 Cần người nhận |

## 🗓️ Đã giao, chưa bắt đầu

| Việc | Hồ sơ | Người nhận | Hạn | Ưu tiên |
|---|---|---|---|---|
| Đổi mật khẩu ở mọi DB/máy từng dùng giá trị cũ | [bug-053](bugs/bug-053-db-init-hong-va-build-can-repo-cha/bug.md) | HiTranquility |  | 🔴 |
| Benchmark ANPR cold/warm và thời gian từng công đoạn | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | Khoa |  | 🟠 |
| Chốt người phụ trách M3/M4 và thứ tự phối hợp console | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | HiTranquility |  | 🟠 |
| Duyệt phần M2 của cổng từ chối Copilot sau đợt code console | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | Khoa |  | 🟠 |
| I-2: tổ chức security review AI Console trước buổi bảo vệ | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | HiTranquility |  | 🟠 |
| Kiểm và cải thiện mức bám tài liệu của câu trả lời Copilot khi similarity cao | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | Khoa |  | 🟠 |
| Restart container `ai` trên stack dev, xác nhận gRPC nạp đúng revision | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | HiTranquility |  | 🟠 |
| Rà revision và tích hợp console/RAG giữa gốc, AI, backend, frontend | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | HiTranquility |  | 🟠 |
| Soát PR ISSUE-019: soát lại chéo audit-6 và chạy convention audit cho phần UI của review-2, kiểm UI… | [ISSUE-019](issues/10-2026/ISSUE-019-console-settings-va-don-audit-006/issue.md) | Dương |  | 🟠 |
| Dựng môi trường demo + 6 tài khoản tách vai, giao phiếu audit AI Console | [ISSUE-020](issues/10-2026/ISSUE-020-ke-hoach-demo-audit-ai-console/issue.md) | HiTranquility |  | 🟠 |
| Nhận phản hồi audit, phân loại và sửa UI/khác | [ISSUE-020](issues/10-2026/ISSUE-020-ke-hoach-demo-audit-ai-console/issue.md) | Claude Code (qua HiTranquility) |  | 🟠 |
| Nhờ GitHub Support xoá các ref `refs/pull/*` của PR cũ còn trỏ tới commit cũ (36 lần xuất hiện) và … | [bug-053](bugs/bug-053-db-init-hong-va-build-can-repo-cha/bug.md) | HiTranquility |  | 🟠 |
| Sửa `AI_GUIDE.md:315` và `AI_USAGE.md:34`, `:79`, `:102` cho khớp việc AI không còn tự bật llama-se… | [ISSUE-019](issues/10-2026/ISSUE-019-console-settings-va-don-audit-006/issue.md) | Khoa |  | 🟡 |
| Thêm Helper Text Lý Do Trả Lại Nhãn và Bộ Chuyển Đổi Vai Trò Nhanh Trên Môi Trường Dev | [SUGGESTION-007](suggestions/10-2026/SUGGESTION-007-helper-text-ly-do-tra-lai-nhan-va-role-quick-switch.md) | @HiTranquility | 2026-10-31 | 🟢 |
| Điều phối gỡ chặn dữ liệu Forecast F0 với analytic | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | HiTranquility |  | 🟢 |
| Đánh giá & calibration phân bố confidence ANPR theo camera — phần AI | [ISSUE-018](issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) | Khoa |  | 🟢 |

## 🚧 Đang làm

| Việc | Hồ sơ | Người nhận | Hạn | Tới đâu |
|---|---|---|---|---|
| Models & Connections trong AI Console — chặng 1: một nguồn model (sửa X2) | [ISSUE-022](issues/10-2026/ISSUE-022-models-connections-mot-nguon-model/issue.md) | @HiTranquility |  | 🚧 In progress — chặng 1 (X2) PR #119; chặng 2 code + test xong (cả DB thật), cùng PR #119; chặng 3–… |
| Sửa `backend/docker-compose.yml` (service AI build) sang `context: ../ai`, `dockerfile: Dockerfile`… | [bug-053](bugs/bug-053-db-init-hong-va-build-can-repo-cha/bug.md) | HiTranquility |  | 🛠️ HiTranquility/IPLMS-Backend#65 (nhánh cùng tên); merge cùng #127 rồi mới nâng gitlink |
| CI `AI · CI` dừng ở bước khởi tạo Postgres vì thiếu `POSTGRES_PASSWORD`, unittest và kiểm khuôn khô… | [bug-055](bugs/bug-055-ci-thieu-postgres-password-test-khong-chay/bug.md) | @HiTranquility |  | 🛠️ Fixing |
| Đọc biển số từ clip ở Vision Lab (IPLMS REQ-021 hướng A) | [ISSUE-025](issues/10-2026/ISSUE-025-doc-bien-so-tu-clip-vision-lab/issue.md) | @HiTranquility | 2026-11-04 | 🚧 In progress |
| Agent tấn công sinh biến thể từ bộ red-team và bắn vào Copilot thật (IPLMS REQ-024 phần A) | [ISSUE-026](issues/10-2026/ISSUE-026-redteam-agent-sinh-bien-the-tan-cong/issue.md) | @HiTranquility | 2026-11-04 | 🚧 In progress — code + test lõi xong; chưa đo với LLM thật |
| Sửa `deployment/registry/push-images-local.{ps1,sh}` và `operations.md:267` sang context `ai/` | [bug-053](bugs/bug-053-db-init-hong-va-build-can-repo-cha/bug.md) | HiTranquility |  | 🛠️ HiTranquility/IPLMS-Deployment#17 |
| Đưa `app/core/` về khuôn domain của ADR-0005 (prompt ra `data/prompts/`, slot tuỳ chọn có tên cố đị… | [ISSUE-023](issues/10-2026/ISSUE-023-khuon-domain-core/issue.md) | @HiTranquility |  | 🚧 In progress — code đã merge, còn chạy `redteam_copilot.py` khi có LLM local |
| Chạy bộ test Knowledge Base với LLM thật (cần `AI_LLM_API_KEY`) | [ISSUE-013](issues/10-2026/ISSUE-013-phan-ai-cua-iplms-issue-009/issue.md) | Dương | 2026-10-15 | 🚧 299 test unit/mock đã pass; chờ key/ollama chạy live |
| Nạp liệu tri thức RAG — phần AI | [ISSUE-012](issues/10-2026/ISSUE-012-phan-ai-cua-iplms-issue-004/issue.md) | Dương | 2026-10-16 | 🚧 Giữ phần ingest/retrieve và test AI; E2E container, caller backend và nối FE chuyển HiTranquility… |
| Làm nốt 1.3 `materialize_dataset` (tải theo manifest + sha256) | [ISSUE-015](issues/10-2026/ISSUE-015-phan-ai-cua-iplms-issue-013/issue.md) | Khoa | 2026-10-16 | 🚧 Đang viết CLI & loader từ private storage |
| Đo ANPR trên test-golden snapshot — phần AI | [ISSUE-014](issues/10-2026/ISSUE-014-phan-ai-cua-iplms-issue-010/issue.md) | Khoa | 2026-10-17 | 🚧 Chuẩn bị test suite & dữ liệu snapshot; phần nối backend/operator và đối chiếu chống tráo do HiTr… |
| Sửa vi phạm so với AI_CONVENTIONS (bổ sung luật lỗi & test doc) | [ISSUE-011](issues/10-2026/ISSUE-011-phan-ai-cua-iplms-audit-004/issue.md) | Dương | 2026-10-19 | 🚧 Đã có báo cáo AUDIT-004; cập nhật doc & gRPC mapping |
| Việc vặt tháng 10/2026 | [CHORE-001](chores/10-2026/CHORE-001-monthly-maintenance/issue.md) | @HiTranquility | 2026-10-31 | 🚧 In progress |
| Định tuyến trực tiếp Root URL và Nâng cấp Copilot Chat Studio 3-Panel | [ISSUE-003](issues/10-2026/ISSUE-003-console-root-routing-copilot-studio/issue.md) | AI Team | 2026-10-31 | 🚧 In progress |
| Việc vặt tháng 11/2026 | [CHORE-002](chores/11-2026/CHORE-002-monthly-maintenance/issue.md) | @HiTranquility | 2026-11-30 | 🚧 In progress |
| Copilot SSE Streaming & Console Telemetry Integration | [ISSUE-002](issues/10-2026/ISSUE-002-copilot-sse-streaming-and-console-telemetry/issue.md) |  |  | 🚧 In progress |
| AI Console nội bộ: DB riêng, 7 vai trò, đăng nhập Google + TOTP, `ai/ui` | [ISSUE-017](issues/10-2026/ISSUE-017-phan-ai-cua-iplms-issue-126/issue.md) | Claude Code |  | 🚧 P1a–P6 + EN (`98c2a88`) + cổng từ chối RAG (`e616fee`) đã code; PR #22, #23 + nhánh xếp chồng chờ… |
| Hoàn thiện phần AI của `khoa-develop`: lọc thẻ `<think>`, rà `guardrail_manager`/`prompt_manager`/`… | [ISSUE-017](issues/10-2026/ISSUE-017-phan-ai-cua-iplms-issue-126/issue.md) | Khoa |  | 🚧 Giữ sửa/test trong AI; HiTranquility phụ trách nối revision/caller và tích hợp tổng thể; giao gốc… |
| Xác nhận cột "đã kiểm/sửa" mục 3b `AI_USAGE.md` cho phần mình nhận (đề Final §5.3, thiếu là −10%) | [ISSUE-017](issues/10-2026/ISSUE-017-phan-ai-cua-iplms-issue-126/issue.md) | Chủ module M1–M4 |  | 🚧 Mới giao 2026-10-18 |
| Củng cố kết nối DB, quản lý tài liệu tri thức, batch upload và tối ưu phân bổ VRAM 4GB cho Console … | [ISSUE-027](issues/10-2026/ISSUE-027-console-tools-and-knowledge-management/issue.md) |  |  | 🚧 IN PROGRESS |

## ⏳ Chờ duyệt

| Việc | Hồ sơ | Người nhận | Tới đâu |
|---|---|---|---|
| Gỡ mật khẩu mặc định khỏi `docker-compose.yml` | [bug-032](bugs/bug-032-ho-so-final-project-lech-voi-repo/bug.md) | HiTranquility | ✅ Fixed — chờ PR |
| Hiệu chỉnh biển số cắt mất ký tự nhưng giữ confidence | [bug-005](bugs/bug-005-plate-correction-mat-ky-tu/bug.md) |  | ✅ Fixed trong nhánh tích hợp — chưa merge / P1 |
| Không có model vẫn trả loại xe suy từ biển như nhận dạng ảnh | [bug-006](bugs/bug-006-vehicle-prior-gia-lam-observation/bug.md) |  | ✅ Fixed trong nhánh tích hợp — chưa merge / P1 |
| Dashboard mới render câu hỏi và câu trả lời bằng innerHTML | [bug-008](bugs/bug-008-dashboard-render-html-khong-escape/bug.md) |  | ✅ Fixed trong nhánh tích hợp — chưa merge / P1 |
| Viết 3 ADR thật mà AI_GUIDE đang gọi là ADR-0008/0009/0010, hoặc sửa AI_GUIDE trỏ ADR có thật | [bug-032](bugs/bug-032-ho-so-final-project-lech-voi-repo/bug.md) | HiTranquility | ✅ Fixed — chờ PR |
| Đưa prompt Copilot ra `data/prompts/` có version | [bug-032](bugs/bug-032-ho-so-final-project-lech-voi-repo/bug.md) | HiTranquility | ✅ Fixed — chờ PR |
| Đăng nhập dev/demo theo vai, cục bộ và an toàn, thay cho `dev-session` | [SUGGESTION-001](suggestions/10-2026/SUGGESTION-001-dang-nhap-dev-cuc-bo-an-toan.md) |  | 🔄 REVIEWING |
| Lưu thuộc tính ảnh khi gán nhãn để đo ANPR theo điều kiện ảnh | [SUGGESTION-004](suggestions/10-2026/SUGGESTION-004-luu-thuoc-tinh-anh-khi-gan-nhan.md) |  | 🔄 REVIEWING |
| Đưa lượt chat đã chấm thành ca hồi quy và so A/B phiên bản prompt ngay trong Copilot Lab | [SUGGESTION-005](suggestions/10-2026/SUGGESTION-005-gom-luot-chat-vao-bo-eval.md) |  | 🔄 REVIEWING |
| Nút nạp mẫu demo Vision Lab không chặn production, nạp lại lỗi 500 và nhãn kẹt bốn mắt | [bug-013](bugs/bug-013-vision-demo-seed-khong-chan-production/bug.md) | @HiTranquility | ✅ Fixed — chờ PR (nhánh `bugfix/bug-013-2026-10-vision-demo-seed-guard`) |
| API giả có hợp đồng và smoke test browser 7 vai × 3 viewport × 2 theme cho `ai/ui` | [SUGGESTION-002](suggestions/10-2026/SUGGESTION-002-mock-api-va-ma-tran-browser-cho-ui.md) |  | 🔄 REVIEWING |
| Lộ trình hoàn thiện AI Console: mức hoàn thiện, vai/quyền, Copilot đa phương tiện, Vision, Forecast | [SUGGESTION-006](suggestions/10-2026/SUGGESTION-006-lo-trinh-hoan-thien-ai-console.md) |  | 🔄 REVIEWING |
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

| Việc | Hồ sơ | Ngày đóng |
|---|---|---|
| `ANPR_MAX_IMAGE_BYTES` / `ANPR_MAX_FILES_PER_REQUEST` mất khỏi `app/core/constants.py` sau khi merg… | [bug-050](bugs/bug-050-anpr-thieu-hang-so-upload-sau-merge/bug.md) | 2026-10-31 |
| Guard Copilot so regex trên chuỗi thô, link và "miễn phí" có ký tự ẩn hoặc chữ Cyrillic đi qua | [bug-049](bugs/bug-049-guard-copilot-khong-chuan-hoa-unicode-truoc-khi-so-regex/bug.md) | 2026-10-31 |
| `server_config.py` mất `from typing import List` sau merge, `app.config` lỗi `NameError` nên servic… | [bug-048](bugs/bug-048-server-config-thieu-import-list-service-khong-khoi-dong/bug.md) | 2026-10-31 |
| Lối vào AI không giới hạn tốc độ và số request đồng thời (Traefik không middleware, gRPC không trần… | [bug-046](bugs/bug-046-loi-vao-ai-khong-gioi-han-toc-do-va-dong-thoi/bug.md) | 2026-10-31 |
| CORS của REST inference phản chiếu mọi origin kèm `allow-credentials: true` | [bug-045](bugs/bug-045-cors-inference-phan-chieu-moi-origin-kem-credentials/bug.md) | 2026-10-31 |
| `/anpr/recognize-many` nhận tới 1000 file mỗi request và chạy ANPR tuần tự từng file | [bug-044](bugs/bug-044-anpr-recognize-many-khong-gioi-han-so-file/bug.md) | 2026-10-31 |
| REST ANPR đọc cả file upload vào RAM, không giới hạn kích thước, không kiểm loại file | [bug-043](bugs/bug-043-anpr-rest-doc-anh-khong-gioi-han-kich-thuoc/bug.md) | 2026-10-31 |
| Prompt Copilot không vào image, service âm thầm chạy prompt dự phòng | [bug-042](bugs/bug-042-prompt-copilot-khong-vao-image-chay-prompt-du-phong/bug.md) | 2026-10-31 |
| Đăng nhập từ `/console/` xong rơi vào trang "Không có trang này" | [bug-033](bugs/bug-033-dang-nhap-tu-goc-console-roi-vao-trang-404/bug.md) | 2026-10-31 |
| Phiên "chờ MFA" tồn đọng trong danh sách Phiên đăng nhập | [bug-030](bugs/bug-030-phien-cho-mfa-ton-dong-trong-danh-sach/bug.md) | 2026-10-31 |
| Fallback kết nối DB sang cổng 5432 rồi tự `CREATE DATABASE` trên một Postgres khác | [bug-029](bugs/bug-029-db-fallback-tu-tao-database-tren-postgres-khac/bug.md) | 2026-10-31 |
| Forecast Simulator luôn chạy baseline vì id bãi trên UI lệch `area_key` của Gold lake | [bug-028](bugs/bug-028-forecast-id-bai-lech-area-key/bug.md) | 2026-10-31 |
| CI unit thiếu runtime dependencies và benchmark fixture bị làm tròn về 0 | [bug-010](bugs/bug-010-ci-fixture-dependencies-va-benchmark-rounding/bug.md) | 2026-10-31 |
| Tách I/O Parquet khỏi `forecast/engines/parquet_lake_reader.py` sang `infra/datalake/` | [ISSUE-024](issues/10-2026/ISSUE-024-tach-io-parquet-lake-reader/issue.md) | 2026-10-30 |
| Không gian làm việc dùng chung giữa tài khoản làm ẩn tính năng; Forecast không có mục menu | [bug-041](bugs/bug-041-khong-gian-lam-viec-dung-chung-an-tinh-nang/bug.md) | 2026-10-27 |
| History hội thoại Copilot ở console không qua rào chắn đầu vào | [bug-040](bugs/bug-040-history-copilot-khong-qua-rao-chan-dau-vao/bug.md) | 2026-10-27 |
| Trang Knowledge ghi cứng 110 màu, theme sáng tương phản chỉ 1.75–2.56:1 | [bug-039](bugs/bug-039-trang-knowledge-mau-ghi-cung-vo-tuong-phan-theme-sang/bug.md) | 2026-10-27 |
| `rag_pipeline.query()` ném NameError `history`, mã audit `engine.reload_llm` thiếu ở UI | [bug-038](bugs/bug-038-rag-query-nameerror-history-va-thieu-ma-audit-reload-llm/bug.md) | 2026-10-27 |
| Gateway Copilot nhận prompt dài tuỳ ý, output guard bị lách bằng cách tách chữ | [bug-037](bugs/bug-037-copilot-gateway-khong-gioi-han-prompt-va-guard-bi-lach-chu/bug.md) | 2026-10-27 |
| "Duyệt nhanh N mẫu khớp 100%" đứt giữa lô thì im lặng và để dòng cũ trên màn hình | [bug-035](bugs/bug-035-duyet-nhanh-theo-lo-dut-giua-chung-im-lang/bug.md) | 2026-10-27 |
