# 🔎 audit-1: Convention audit — ai bug-028 + IPLMS REQ-022 F1–F3 (nhãn nguồn số forecast)

> Mẫu của [convention audit](../../../../../../skills/iplms-code-review/references/convention-audit.md) (IPLMS ADR-0052). Auditor viết; fixer chỉ sửa cột "Đã sửa" và trạng thái `Fixed`; auditor đặt `Verified`/`Reopened` và Kết luận.

| | |
|---|---|
| **Kết luận** | ✅ Đạt sau soát lại (2026-10-28): A-1…A-4, A-6 Verified; A-5 Deferred (P3) |
| **Vòng** | 2/3 |
| **Phạm vi** | nhánh `bugfix/bug-028-2026-10-forecast-area-key-and-source-label`: ai `origin/develop...84dc0fb` (16 file); backend `origin/develop...1dd90d2` (9 file); frontend `origin/develop...710f605` (12 file); gốc staged `proto/forecast_service.proto` (1 file) |
| **Auditor** | Claude Code, subagent convention-auditor, 2026-10-28. Không viết code chặng này |
| **Fixer** | agent fixer do người điều phối giao (vòng 2, sửa ở working tree, chưa commit) |
| **Máy quét** | `check_diff.py --range origin/develop...HEAD` ở ai/backend/frontend, `--staged` ở gốc → 0 FAIL, 0 WARN cả 4 (lần 1, auditor tự chạy lại) · soát lại vòng 2: `check_diff.py` (nhánh + working tree) ở ai/backend/frontend, `--staged` ở gốc → 0 FAIL, 0 WARN cả 4 |
| **Quy ước đã nạp** | `ai/docs/standards/AI_CONVENTIONS.md` §1–§3; `ai/ui/DESIGN.md` (Ngôn ngữ VI/EN, Luật Hallmark 1–8); `backend/docs/standards/BACKEND_CONVENTIONS.md` §9.1–§9.4; `.claude/rules/frontend.md` (UI 1–6, Shared vs Ui, barrel); `docs/standards/frontend/FRONTEND_CONVENTIONS.md` §13 i18n; `frontend/DESIGN.md` §4; REQ-022 §3 F1–F3 |

## Findings

| # | Mức | Loại | `file:line` | Luật bị vi phạm | Mô tả | Cách sửa đề xuất | Trạng thái | Đã sửa |
|---|---|---|---|---|---|---|---|---|
| A-1 | P2 | quy-ước | `ai/ui/src/pages/Tools/components/ForecastSimulator/ForecastSimulator.tsx:111`, `:353-357` | `ai/ui/DESIGN.md` "Luật Hallmark áp dụng" mục 2 (không bịa số/trạng thái) và mục 7 (mọi màn hình dữ liệu có loading, empty, error kèm mã lỗi và "Thử lại") | `useForecastAreas()` lỗi (403, 500, mạng) thì `lakeAreas = []` và option hiện "Gold lake chưa có bãi nào". Đó là một trạng thái sai. `libs/query-client.ts` không có toast lỗi chung nên người dùng không thấy lỗi, cũng không có nút thử lại. | Khi `lakeAreasQuery.isError` thì hiện `ErrorBlock error={lakeAreasQuery.error} onRetry={() => void lakeAreasQuery.refetch()}` (`components/common/Ui/feedback/LoadState.tsx:19`), không hiện câu "lake rỗng". Thêm test: `/tools/forecast/areas` trả 500 thì không có option "Gold lake chưa có bãi nào" và có nút thử lại. | Verified | Có `isError` thì option ghi `feedback.loadFailed` và dưới ô chọn hiện `ErrorBlock` + "Thử lại" (`ForecastSimulator.tsx`); test mới "shows a load error with retry…" (areas trả 500). |
| A-2 | P2 | quy-ước | `backend/src/modules/Analytics/services/admin-analytics.service.ts:20` | BACKEND_CONVENTIONS §9.1: "[MUST] Import qua alias `@infrastructures/Ai`" | Import bằng đường tương đối `'../../../infrastructures/Ai/ai.constants'`. Mọi chỗ khác trong `modules/` dùng `@infrastructures/Ai`, và barrel `infrastructures/Ai/index.ts` đã `export * from './ai.constants'`. | `import { FORECAST_BASELINE_SOURCE } from '@infrastructures/Ai';` | Verified | Import `FORECAST_BASELINE_SOURCE`, `ForecastDataSource` từ `@infrastructures/Ai`. |
| A-3 | P2 | hợp-đồng | `proto/forecast_service.proto:43`, `:56` (cả 3 bản); `backend/src/infrastructures/Ai/providers/forecast-ai.interface.ts:24`, `:38`; `backend/src/modules/Analytics/dtos/admin-forecast.dto.ts:81`, `:95`; `backend/src/modules/Analytics/services/admin-analytics.service.ts:23`; `frontend/packages/shared/src/components/Ui/data-display/ForecastSourceBadge.tsx:6`; `frontend/packages/shared/src/types/common/ai.type.ts:76` | BACKEND_CONVENTIONS §9.4: "[MUST] Từ vựng do AI service sở hữu … khai `enum` trong proto"; §9.1: `ai.types.ts` mirror enum proto | `data_source` là từ vựng đóng do AI sở hữu (`lakehouse_parquet`/`clickhouse_marts`/`heuristic_baseline`) nhưng khai `string`, tập giá trị chỉ nằm trong comment. Ở 3 tầng nó là `string` trần. Backend còn thêm một giá trị riêng (`backend_estimate`) vào cùng trường, và FE chép lại literal này (`OFFLINE_SOURCE`). Gõ sai một giá trị thì không có lỗi biên dịch, chỉ lặng lẽ rơi về "sơ bộ". | (a) Thêm `enum ForecastDataSource { FORECAST_DATA_SOURCE_UNSPECIFIED = 0; LAKEHOUSE_PARQUET = 1; CLICKHOUSE_MARTS = 2; HEURISTIC_BASELINE = 3; }` (UNSPECIFIED thay cho xử lý chuỗi rỗng của AI cũ). Mirror union trong `ai.types.ts`. Đổi `dataSource` ở DTO backend và type FE thành union, gồm cả `backend_estimate`. Đồng bộ 3 bản proto rồi chạy `proto:sync` + `compile_proto.py`. Lưu ý: `enums: String` trả tên enum nên giá trị FE nhận sẽ đổi. (b) Nếu giữ `string`, ví dụ để khớp REST `AreaOccupancyForecastResult.data_source` đang là chuỗi, ghi ngoại lệ vào REQ-022 §9.2 có techlead quyết, và vẫn thêm union type ở BE/FE. | Verified | Chọn (a). Proto thêm `enum ForecastDataSource` (UNSPECIFIED/LAKEHOUSE_PARQUET/CLICKHOUSE_MARTS/HEURISTIC_BASELINE), trường 4 đổi kiểu sang enum ở cả 2 message, 3 bản proto chép lại, `compile_proto.py` chạy lại. Python: `app/core/enums.py::ForecastDataSource` + canh ở `test_enums_match_proto.py`; mapper `ForecastDataSource.Value`. Backend: union `ForecastDataSource` trong `ai.types.ts`, provider đổi UNSPECIFIED → HEURISTIC_BASELINE; admin dùng `AdminForecastDataSource` (enum AI + `BACKEND_ESTIMATE`), REST lạ/thiếu → baseline. FE: union `ForecastDataSource` trong `ai.type.ts`, badge bỏ literal riêng. Hệ quả: REST AI và API backend giờ trả tên enum viết hoa. |
| A-4 | P2 | đúng-sai | `frontend/packages/platform/src/pages/Common/Dashboard/components/Dashboard/CityOccupancyHeatmap.tsx:383-388`, `:398-415` | REQ-022 F2 (AC chặng): "Mọi màn hình hiển thị số dự báo đều có nhãn nguồn số theo `data_source`/`is_fallback`" | Banner có hai số dự báo lấy từ hai request độc lập: `getAreaOccupancyForecast` và `getAreaSurgeMultiplier`, mỗi response có `dataSource`/`isFallback` riêng. Badge chỉ đọc `forecastData`. Ca 1: forecast AI đọc từ lake (history), còn surge rơi `backend_estimate`. Khi đó "Surge Multiplier: 1.5x" nằm dưới nhãn "Ước lượng theo lịch sử". Ca 2: forecast lỗi, surge thành công. Khi đó số surge hiện mà không có nhãn nào. Thuộc phạm vi bug-028/REQ-022 F2 có sẵn nên không mở `bug-NNN` mới. | Gắn `ForecastSourceBadge` riêng cho `surgeData` trong `surge-multiplier-badge`, hoặc gộp hai nguồn thành một nhãn: history chỉ khi cả hai là history. Thêm test cho ca forecast history + surge `backend_estimate`. | Verified | `surge-multiplier-badge` có `ForecastSourceBadge` riêng từ `surgeData`; test heatmap kiểm hai nhãn khác nguồn (forecast baseline, surge lake) và nhãn surge nằm trong khối surge. |
| A-5 | P3 | quy-ước | `frontend/packages/client/src/pages/Anonymous/Parking/components/Detail/OccupancyForecastWidget.tsx:107-110`; `frontend/packages/operator/src/pages/Owner/Facility/components/FacilityDetail/PricingTab.tsx:264`, `:267`, `:279` | FRONTEND_CONVENTIONS §13: "`useTranslation()`; **không** hardcode chuỗi hiển thị" | Các dòng viết lại vẫn hardcode tiếng Việt, đặt ngay cạnh badge đã i18n. Ở EN, màn hình lẫn hai thứ tiếng. Chuỗi cũ vốn đã hardcode (nợ i18n chung) nên để P3. | Đưa vào `client`/`operator` `locales/{vi,en}`, hoặc `Deferred` sang đợt bóc i18n từng trang kèm hồ sơ theo dõi. | Deferred | Giữ cho đợt bóc i18n từng trang (chủ dự án bảo làm dần, xem memory i18n-campaign); hai màn hình này vốn hardcode toàn bộ. Theo dõi ở REQ-022 §9.3 "Chưa làm". |
| A-6 | P3 | test | `ai/app/core/forecast/services/forecast_service.py:145-149`; `frontend/packages/shared/src/components/Ui/data-display/ForecastSourceBadge.tsx:27-31` | [code review checks](../../../../../../skills/iplms-code-review/references/convention-audit.md) mục 3.4: test phải chứng minh đúng điều cần chứng minh | `_merge_provenance` có luật "một khung baseline thì cả kết quả là baseline" nhưng chỉ được test với 2 khung cùng nguồn (Thứ Năm 08h–09h, đều có trong lake). Chưa có ca trộn. Nhánh `backend_estimate` → `offlineHint` của badge chưa có test. Test heatmap mock luôn badge nên platform không phủ badge thật. | Thêm test AI: `target_timestamp` Thứ Năm 23:00, `forecast_hours=2` (khung sau sang Thứ Sáu, không có trong lake) → `("heuristic_baseline", True)`. Thêm test cho badge `dataSource="backend_estimate"` → câu `offlineHint`. | Verified | AI: `test_khung_gio_tron_lake_va_baseline_thi_ca_ket_qua_la_baseline` (22:00 thứ Năm → 02:00 thứ Sáu). FE: `PricingTab.test.tsx` thêm 2 test `ForecastSourceBadge` thật (BACKEND_ESTIMATE → offlineHint; isFallback=true không bao giờ là history). |

Trạng thái: `Open` → `Fixed` (fixer) → `Verified` (auditor) · `Reopened` · `Deferred` (P3, kèm hồ sơ theo dõi).
Loại: `quy-ước` · `hợp-đồng` · `đúng-sai` · `test` · `bảo-mật` · `hiệu-năng` · `tài-liệu`.

### Theo loại

| Loại | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| quy-ước | 0 | 0 | 2 | 1 |
| hợp-đồng | 0 | 0 | 1 | 0 |
| đúng-sai | 0 | 0 | 1 | 0 |
| test | 0 | 0 | 0 | 1 |

### Đã soát, đạt

- **Proto 3 bản:** `ai/proto`, `backend/src/infrastructures/Ai/proto`, `root/proto` cùng md5 `69879c74…`. Tag mới 4, 5 không tái dùng tag cũ (§9.4). Mapper `to_*_response` đúng chiều (AI_CONVENTIONS §3). Stub trong `generated/` không bị sửa tay.
- **Hợp đồng hai đầu:** AI DTO → mapper → proto → loader `keepCase:false, defaults:true` (`ai.module.ts:36-39`) → `ForecastAiProvider.withProvenance` → `OccupancyForecastResponse.fromGrpc` (`ai-copilot.service.ts:78-84`) → FE `ai.type.ts` → `OccupancyForecastWidget`/`PricingTab`. Admin: AI REST `AreaOccupancyForecastResult`/`SurgeMultiplierResult` (`forecast_dto.py:82-83`, `:94-95`) → `aiProvenance` → `admin-forecast.dto.ts` → FE `adminAnalytics.types.ts` → heatmap. Tên field và kiểu khớp. Thiếu nguồn đều rơi về baseline ở cả BE và FE.
- **Console REST:** `GET /tools/forecast/areas` dùng `require_permission("ai:metrics:read")` giống `/forecast/simulate`, và service gọi lại `access_policy.require`. Envelope `BaseResponse.ok([...])` khớp `apiClient.getOne`. `queryKeys.tools.forecastAreas()` theo factory. Hook và type có trong barrel (`hooks/queries/index.ts`, `types/tool/index.ts`). i18n VI/EN đủ khoá (`en: Messages`).
- **FE shared:** `ForecastSourceBadge` nhận props nên đặt ở `Ui/data-display/` là đúng. Named export, có trong `shared/src/index.ts:70`. CSS chỉ dùng token `--space-2`/`--color-muted`/`--text-xs`, cả 3 token có trong `index.css` của 3 app, không hex/px. Biến thể `success`/`warning` có trong `Badge`. Khoá `forecastSource.*` có cả `vi`/`en` `common.json`, namespace mặc định `common` (`libs/i18n.ts:19`).
- **F3:** grep "AI Forecast|Dự báo AI|AI dự báo" trong `frontend/packages/*/src` (trừ test) chỉ còn comment `CityOccupancyHeatmap.tsx:381`. Heatmap bỏ được badge hex/glow (`#dcfce7`, `boxShadow`).
- **AI core:** `core/` không import grpc/pb2; `api/` không import `engines/` (§1). Lọc `is_fallback` trước khi nạp cache (`forecast_service.py:103-104`) có test hồi quy `test_bai_ngoai_lake_khong_bi_gan_nhan_lake_sau_khi_nap`.

## WARN đã xét

Không có WARN (máy quét 0 FAIL, 0 WARN ở cả 4 repo).

## Bug đã mở

Không có. A-4 thuộc phạm vi hồ sơ có sẵn ([bug-028](../bug.md), IPLMS REQ-022 F2) nên sửa trong chặng này.

## Ngoài phạm vi (nợ cũ nhìn thấy)

- `analytic/etl/parquet_lake_exporter.py:240-242`: `_generate_occupancy_telemetry_fallback` ghi dữ liệu tổng hợp vào gold mà không đánh dấu. Vì vậy, sau chặng này, số dựng từ dữ liệu tổng hợp vẫn mang nhãn "Ước lượng theo lịch sử" (bug.md mục "Còn lại" đã ghi). **Chưa có hồ sơ theo dõi** ở `analytic/docs/projects/bugs/`. Auditor không mở vì việc đó cần nhánh riêng ở analytic (một hồ sơ một nhánh); người điều phối nên mở `bug-NNN` ở namespace analytic.
- `backend/src/modules/AiCopilot/services/ai-copilot.service.ts:86-94`: tariff trả thẳng interface gRPC ra controller, không có `fromGrpc` (BACKEND §9.3 [NEVER]). Field proto mới vì vậy tự lộ ra API công khai.
- `backend/src/modules/Analytics/dtos/admin-forecast.dto.ts`: hậu tố `.dto.ts` (BACKEND §9.3).
- `ai/app/core/forecast/dtos/forecast_dto.py:83`, `:95`: DTO REST mặc định `is_fallback=False`, lệch với DTO gRPC mới (`True`).
- `frontend/packages/platform/.../CityOccupancyHeatmap.tsx:306-430`: inline style hex/px. Nền banner `#f0fdf4` vẫn xanh cả khi số là baseline.
- `frontend/packages/client/.../OccupancyForecastWidget.tsx:46`: emoji 📈 trong tiêu đề (frontend/DESIGN.md §4 luật 1).
- `ai/app/api/rest/routes/console_tools_controller.py`: model Pydantic khai inline trong controller thay vì `schemas/`. Theo khuôn sẵn có của file (AI_CONVENTIONS §3 REST).

## Gợi ý (không có luật, không chặn)

- `ForecastSourceBadge` khi `showHint=false` chỉ để câu giải thích trong `title`. Client là app mobile-first nên trên màn cảm ứng không xem được. Cân nhắc `showHint` ở client hoặc `aria-describedby`.
- `ForecastService.list_lake_areas` đọc toàn bộ lake ở mỗi request, không cache. Hiện ổn với lake dev 96 dòng; cần cache khi có lake thật.

## Kiểm chứng auditor đã chạy

| Lệnh | Kết quả |
|---|---|
| `check_diff.py` ×4 (ai/backend/frontend range, gốc staged) | PASS: 0 FAIL, 0 WARN |
| md5 3 bản `forecast_service.proto` | PASS: trùng nhau |
| `ai/.venv python -m unittest test.test_forecast_lake_areas` | PASS: 6/6 |
| `backend: npx jest forecast-ai.provider.spec.ts admin-analytics.service.spec.ts` | PASS: 2 suite, 6 test |
| `ai/ui: npx vitest run …/ForecastSimulator` | PASS: 7/7 |
| `operator`/`platform` vitest cho `PricingTab.test.tsx`, `CityOccupancyHeatmap.test.tsx` | BLOCKED: `vitest-pool: Failed to start forks worker` trên máy này (REQ-022 9.3 ghi cần shim zstd cho Node 22.14). Chưa tự xác nhận |
| Build/tsc frontend, browser 3 app + Console (L1–L8) | NOT RUN. Gap runtime: auditor chỉ đọc code |

## Soát lại

Mỗi vòng (lượt auditor) một dòng; tối đa 3 vòng, vòng 2–3 chỉ soát delta của fixer + finding `Fixed`. `Tree` = `git write-tree` của index lúc bắt đầu vòng (mỗi repo/submodule có diff một tree).

| Lần | Ngày | Tree | Finding đã soát | Kết quả |
|---|---|---|---|---|
| 1 | 2026-10-28 | ai `e9f19796038d5948f9f9055f36bc57ac24a8b8aa` · backend `a9193212cefebc8be161a0d34891c383b9d751fc` · frontend `f1d914eb2a12b05895eb3b9d5cbe9d9e4ddd27a8` · gốc `292542f4ca2b8502f1ade1ff53024b215042ca36` | A-1…A-6 | Open (4 P2, 2 P3) |
| 2 | 2026-10-28 | ai `e9f19796038d5948f9f9055f36bc57ac24a8b8aa` · backend `a9193212cefebc8be161a0d34891c383b9d751fc` · frontend `f1d914eb2a12b05895eb3b9d5cbe9d9e4ddd27a8` (index không đổi; delta sửa nằm ở working tree, soát bằng `git diff HEAD`) · gốc `3f1583a19c496bf1f11775f011079911b94acac6` | A-1, A-2, A-3, A-4, A-6 (Fixed) + A-5 (Deferred) + mọi chỗ fixer chạm thêm | A-1…A-4, A-6 Verified; A-5 Deferred chấp nhận; 0 finding mới |

### Ghi chú soát lại vòng 2

- **A-1 Verified:** `ForecastSimulator.tsx` có nhánh `isError`. Option hiện `feedback.loadFailed` (khoá có ở `vi.ts:21`, `en.ts:18`), dưới ô chọn có `ErrorBlock` + `refetch`. Test mới cho ca 500 kiểm `role=alert`, nút "Thử lại", và không còn câu "lake rỗng".
- **A-2 Verified:** `admin-analytics.service.ts` import từ `@infrastructures/Ai`, không còn đường tương đối.
- **A-3 Verified (phương án a):** `enum ForecastDataSource` có `UNSPECIFIED = 0`. 3 bản proto cùng md5 `6974c9bd…`, bản gốc staged khớp `ai/proto` khi bỏ CR. Python `app/core/enums.py` được canh bằng `test_forecast_data_source_khop`. Mapper dùng `ForecastDataSource.Value`. `ai.types.ts` có union mirror; provider đổi `UNSPECIFIED`/rỗng thành `HEURISTIC_BASELINE`. Admin có `AdminForecastDataSource`, nguồn lạ hoặc thiếu đều về baseline. FE có union `ForecastDataSource` trong `ai.type.ts` (export qua barrel `index.ts:452`), badge bỏ literal riêng. Grep chuỗi viết thường trong code ai/backend/frontend: chỉ còn một comment test và văn bản lịch sử ở `bug.md`. Hệ quả đổi giá trị sang chữ hoa ở REST AI và API backend: bên tiêu thụ duy nhất (backend `aiProvenance`, FE badge, test) đã đổi theo. `proto/check_proto_sync.py` chạy từ `root/` báo "0 file ở backend" vì worktree gốc không checkout submodule; đây là lỗi bố cục của worktree, không phải lệch proto (md5 trùng nhau).
- **A-4 Verified:** `surge-multiplier-badge` có `ForecastSourceBadge` riêng. Test kiểm hai nhãn khác nguồn và nhãn surge nằm trong khối surge.
- **A-5 Deferred (P3) chấp nhận:** lý do hợp lệ (đợt bóc i18n từng trang). **Lưu ý:** REQ-022 §9.3 hiện **chưa có** dòng theo dõi mà ô "Đã sửa" nhắc tới (grep REQ-022 không thấy). Người điều phối cần thêm dòng đó khi cập nhật REQ. Việc này không chặn Kết luận vì không phải P0–P2.
- **A-6 Verified:** có test ca trộn 22:00 thứ Năm → 02:00 thứ Sáu ra `(HEURISTIC_BASELINE, True)`. Có 2 test badge thật (`BACKEND_ESTIMATE` → offlineHint; `isFallback=true` không bao giờ là history).
- **Chỗ fixer chạm thêm:** `test_forecast_service.py` đổi literal theo enum. Spec admin fallback mock `fetch` lỗi một lần (`mockRejectedValueOnce`), không còn phụ thuộc máy có AI ở :8000. Test surge fallback có sẵn vẫn gọi fetch thật nhưng nằm ngoài delta. Không có finding mới.

| Lệnh (auditor chạy lại, vòng 2) | Kết quả |
|---|---|
| `check_diff.py` ×4 | PASS: 0 FAIL, 0 WARN |
| `ai/.venv python -m unittest test.test_forecast_lake_areas test.test_enums_match_proto test.test_forecast_service` | PASS: 31 test |
| `ai/ui`: `vitest run …/ForecastSimulator`, `tsc --noEmit` | PASS: 8/8; tsc sạch |
| `backend`: `jest` 2 spec forecast/admin, `tsc --noEmit` | PASS: 6/6; tsc sạch |
| `frontend/packages/shared`: `tsc --noEmit` | PASS |
| `operator` `PricingTab.test.tsx`, `platform` `CityOccupancyHeatmap.test.tsx` (`NODE_OPTIONS=--require zstd-shim.cjs`) | PASS: 5/5, 11/11 |
| Browser 3 app + Console (L1–L8) | NOT RUN: gap runtime, như vòng 1 |
