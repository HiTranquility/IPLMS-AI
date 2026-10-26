# 🏷️ ISSUE-018: Kế hoạch theo thành viên (chủ dự án chốt 2026-10-19)

> **Đích:** `docs/projects/issues/10-2026/ISSUE-018-ke-hoach-theo-thanh-vien/issue.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 📝 Dự kiến — chưa bắt đầu |
| **Người phụ trách** | — |
| **Phạm vi** | `ai` |
| **Bắt nguồn từ** | IPLMS REQ-006 F10 / IPLMS ISSUE-125 review-4 |
| **Ngày tạo** | 2026-10-25 |
| **Người viết** | Claude — chuyển từ BOARD viết tay khi BOARD chuyển sang sinh từ Meta hồ sơ (IPLMS ADR-0060) |

> BOARD sinh từ Meta và bảng `📋 Việc trên BOARD` dưới đây (IPLMS ADR-0060): đổi người nhận/hạn/trạng thái một việc thì sửa dòng của nó ở đây, **[NEVER]** sửa `BOARD.md`.

## Mục tiêu

Chủ dự án chọn B và yêu cầu hoạch định lại ngày 2026-10-19: **HiTranquility phụ trách phần tổng thể/tích hợp**, Khoa/Dương phụ trách phần AI. **Dự kiến cho** chưa có nghĩa đã bắt đầu. Không chia đều số việc; không tự ấn định hạn tuần hoặc suy ra tiến độ thực tế từ hạn cũ.
Thứ tự là gợi ý trong từng người, sau khi rà việc đang làm và review 🔴 ở mục 🙋. HiTranquility thực hiện nối tiếp theo điều kiện, không phải 7 việc đồng thời. Chuyển dòng sang 🚧 khi xác nhận bắt đầu và hạn. M3/M4 vẫn cần chốt người; Claude Code là tác nhân viết code, không thay người tích hợp.
**Làm rõ theo chủ dự án:** demo liên vai là các vai trên UI của IPLMS-AI, do Dương phụ trách. Thao tác giữa `ui/` và phần API/service trong cùng repo IPLMS-AI vẫn thuộc phạm vi AI. Nếu kịch bản cần sửa code ở repo gốc, backend, frontend, analytic hoặc repo khác, ghi điểm chặn và báo chủ dự án để chốt phần tích hợp với HiTranquility; không tự mở rộng demo.
Kế hoạch mới nhất theo IPLMS REQ-006 F10 / ISSUE-125 review-4: 16 việc dự kiến (Khoa 4, Dương 5, HiTranquility 7), gồm 4 việc kỹ thuật mới thêm. I-3 vẫn thuộc Dương trong IPLMS-AI; các việc tổng thể giữ HiTranquility. Không chạy demo, model, LLM, đổi quyền hoặc thao tác stack trong lượt bổ sung kế hoạch.

## 📋 Việc trên BOARD

| Việc | Người nhận | Hạn | Ưu tiên | Trạng thái | Hồ sơ gốc | Ghi chú |
|---|---|---|---|---|---|---|
| Duyệt phần M2 của cổng từ chối Copilot sau đợt code console | Khoa | — | 🟠 | 📝 Dự kiến — chưa bắt đầu | IPLMS ISSUE-126 review-7 OPEN-01; BOARD ✅ ngày 2026-10-18 | bắt đầu khi: Chốt revision cần duyệt với Dương; dành được thời gian sau việc M2 đang nhận · đầu ra: Nhận xét chấp nhận/cần sửa, ghi rõ model, ngưỡng và rủi ro câu có similarity cao; chưa tự thay ngưỡng |
| Đánh giá & calibration phân bố confidence ANPR theo camera — phần AI | Khoa | — | 🟢 | 📝 Dự kiến — chưa bắt đầu | IPLMS PROB-045 | bắt đầu khi: `materialize_dataset` và test-golden được xác minh, có tập theo camera đủ dùng · đầu ra: Báo cáo phân bố/sai số theo camera cho HiTranquility đối chiếu tích hợp; chưa áp ngưỡng khi chưa duyệt |
| Kiểm và cải thiện mức bám tài liệu của câu trả lời Copilot khi similarity cao | Khoa | — | 🟠 | 📝 Dự kiến — chưa bắt đầu | IPLMS ISSUE-126 review-7 S2, BUG-03 | bắt đầu khi: Chốt revision và tập hồi quy với Dương; dùng LLM local và dữ liệu test được phép · đầu ra: Tái hiện TC-12/TC-17/HO-13, lập kiểm chứng câu trả lời bám nguồn; báo trước/sau và tỷ lệ từ chối nhầm trên câu hợp lệ; đề xuất kiểm đầu ra trước khi đổi hành vi mặc định |
| Benchmark ANPR cold/warm và thời gian từng công đoạn | Khoa | — | 🟠 | 📝 Dự kiến — chưa bắt đầu | IPLMS PROB-045 §Baseline và ANPR profiling | bắt đầu khi: Có fixture ảnh AI được phép và model sẵn local; không tải weights mới hoặc restart stack chung · đầu ra: Đo ≥ 3 lượt cold và ≥ 100 lượt warm, p50/p95 và CPU/RAM; tách decode/detect/crop/OCR/classify nơi đo được; lưu phiên bản model, cấu hình và phần cứng để chạy lại |
| I-3: demo liên vai trên UI IPLMS-AI bằng `iplms-demo-loop` | Dương | — | 🟢 | ✅ Done (2026-10-25) — ISSUE-010 (`CrossRoleDemoLoop.test.tsx` 5/5 PASS) | IPLMS ISSUE-126; UI và quyền của AI Console | bắt đầu khi: Có tài khoản test theo vai, dữ liệu test AI và môi trường console local; bước thiếu dữ liệu ghi chặn, không tự cấu hình A2/backend · đầu ra: Kịch bản data engineer, annotator, reviewer, ML engineer, lead và các vai liên quan theo quyền hiện có; kiểm UI, lưu/tải lại và từ chối sai quyền trong AI; cần sửa code ngoài IPLMS-AI thì báo chủ dự án |
| Bổ sung test hồi quy quyền 7 vai Console trên UI/API | Dương | — | 🟠 | ✅ Done (2026-10-25) — ISSUE-008 (`test_console_access.py` 26/26 PASS) | IPLMS ISSUE-126; `app/core/console/engines/access_policy.py` | bắt đầu khi: Rà test đã có và lập ma trận vai/thao tác; dùng tài khoản hoặc fixture cô lập trong AI · đầu ra: Ma trận đủ 7 vai và quyền hiện có, có test allow/deny cho ca còn thiếu; nút ẩn không thay kiểm API; ghi bằng chứng test tự động, không chỉ checklist demo |
| Nâng cấp toàn bộ phần Vision: model + pipeline ANPR (detector, OCR, hậu xử lý biển số) và Vision Lab trên Console (gán nhãn, duyệt bốn mắt, ANPR sandbox) — lập ISSUE riêng, chốt phạm vi và chỉ số đo trước khi code | Dương | — | 🟠 | ✅ Done (2026-10-26) — [ISSUE-020](../ISSUE-020-vision-anpr-pipeline-and-vision-lab-upgrade/issue.md) | Chủ dự án giao 2026-10-26 | Dương làm cả model lẫn UI; đổi checkpoint/weights phải hỏi chủ dự án; Khoa giữ benchmark/calibration ANPR làm thước đo trước–sau |
| Chuyển ứng viên Eval từ `var/eval_candidates.json` vào bảng DB có retention (finding A-37 phần còn lại) — qua cổng schema (`iplms-schema-design`) trước khi viết migration | Dương | — | 🟡 | ✅ Done (2026-10-26) — bảng `copilot_eval_candidate` + retention + redact (`test_console_copilot_lab.py`) | ai ISSUE-019 A-37 | Code + test; giữ `redact` như hiện tại |
| Seed demo trung thực: bỏ số tự đặt trong lý do đề xuất ngưỡng (`seed_console_demo.py` mục 4, A-71), sửa comment còn ghi promote (A-70) và viết test chạy seed trên DB test (A-7) | Dương | — | 🟡 | ✅ Done (2026-10-26) — sửa A-7/A-70/A-71 trong `seed_console_demo.py` + `test_seed_console_demo.py` | ai ISSUE-019 A-7 | Code + test DB (`AI_TEST_DATABASE_URL`) |
| Bổ sung test hồi quy UI khi API lỗi, timeout hoặc phiên hết hạn | Dương | — | 🟠 | ✅ Done (2026-10-25) — ISSUE-009 (`client.test.ts` 7/7 + `CopilotLabPage.test.tsx` 6/6 PASS) | IPLMS ISSUE-126; `ui/README.md` và test UI hiện có | bắt đầu khi: Đối chiếu test đã có; mô phỏng lỗi trong test local của `ai/ui`, không phá môi trường chung · đầu ra: Phủ ca còn thiếu cho 401/403/500/timeout tại màn hình liên quan; không báo lưu thành công giả, xử lý retry/đăng nhập theo luồng hiện có; chạy lại suite UI và ghi kết quả |
| Restart container `ai` trên stack dev, xác nhận gRPC nạp đúng revision | HiTranquility | — | 🟠 | 📝 Dự kiến — chưa bắt đầu | IPLMS bug-006 | bắt đầu khi: Có cửa sổ thao tác stack dùng chung; xác nhận tác động trước khi restart · đầu ra: Endpoint/version và kiểm gRPC/warmup; Khoa hỗ trợ đo ANPR; chuyển từ dòng Khoa hạn cũ 2026-10-14, chưa coi HiTranquility đã bắt đầu |
| Rà revision và tích hợp console/RAG giữa gốc, AI, backend, frontend | HiTranquility | — | 🟠 | 📝 Dự kiến — chưa bắt đầu | IPLMS ISSUE-126 review-7; IPLMS ISSUE-004 | bắt đầu khi: Khoa/Dương bàn giao kết quả AI; kiểm `review-7.md`/`eval_copilot_e2e.py` lệch sau `e616fee`; CI và quyền môi trường sẵn sàng cho phần chạy thật · đầu ra: Bảng revision/gitlink, hợp đồng caller và kết quả E2E RAG; chưa merge/deploy hoặc đổi trạng thái chặn khi chưa có bằng chứng |
| I-2: tổ chức security review AI Console trước buổi bảo vệ | HiTranquility | — | 🟠 | 📝 Dự kiến — chưa bắt đầu | IPLMS ISSUE-126; IPLMS ADR-0048, ADR-0051 | bắt đầu khi: Xác định revision; có tài khoản test và môi trường local cô lập · đầu ra: Checklist đăng nhập/phiên/quyền/PII và bằng chứng từ chối sai quyền; người review độc lập với người viết phần quyền |
| Chốt người phụ trách M3/M4 và thứ tự phối hợp console | HiTranquility | — | 🟠 | 📝 Dự kiến — chưa bắt đầu | IPLMS ISSUE-126 — bảng chia việc M0–M4 | bắt đầu khi: Xác nhận lịch và năng lực của nhóm; có thể chốt sớm để gỡ phụ thuộc cho các việc trước · đầu ra: Người được xác nhận, phạm vi file/module và người duyệt; không mặc định Khoa/Dương nhận phần ngoài AI |
| Điều phối gỡ chặn dữ liệu Forecast F0 với analytic | HiTranquility | — | 🟢 | 📝 Dự kiến — chưa bắt đầu | IPLMS ISSUE-014 F0; IPLMS PROB-039 | bắt đầu khi: Xác định người cung cấp export/capacity; chưa bật model phục vụ · đầu ra: Chốt nguồn dữ liệu, timezone và lịch sử capacity; AI chỉ backtest khi dữ liệu đủ điều kiện |

### Phạm vi theo thành viên

| Người | Phạm vi phụ trách trong kế hoạch này | Bàn giao / phối hợp |
|---|---|---|
| Khoa | Đo/benchmark/calibration ANPR, phần M2 Copilot và hướng dẫn module trong `ai/` (từ 2026-10-26 phần nâng cấp model Vision chuyển sang Dương) | Bàn giao kết quả đo, fixture và test AI cho HiTranquility; không tự nhận sửa caller hoặc cấu trúc repo gốc |
| Dương | RAG/KB, workflow, test AI, demo liên vai trên UI IPLMS-AI; từ 2026-10-26 thêm toàn bộ Vision (model + pipeline ANPR + Vision Lab) và soát audit/UI/conventions | Tự kiểm UI/API trong IPLMS-AI; cần sửa code ngoài repo thì báo chủ dự án; HiTranquility lo phần tích hợp được chốt |
| HiTranquility | Repo gốc, liên kết thư mục/module, proto chung, CI/stack, tích hợp backend/frontend/analytic | Chủ trì phần tổng thể; hỗ trợ khi demo AI phát sinh điểm chặn ngoài repo và chủ dự án chốt; không nhận thay demo UI của Dương |

## Tiêu chí chấp nhận

- [ ] Mỗi dòng ở bảng trên chuyển sang ✅ kèm bằng chứng (ở đây hoặc ở hồ sơ gốc).
- [ ] Hết dòng mở → Trạng thái hồ sơ này ✅ + **Ngày đóng**.

## Hồ sơ liên quan

- IPLMS REQ-006 F10 / IPLMS ISSUE-125 review-4 — mô tả đầy đủ và bằng chứng nằm ở đó.
