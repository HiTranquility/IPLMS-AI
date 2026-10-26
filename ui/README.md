# AI Console UI (`ai/ui`)

Giao diện nội bộ của bộ phận AI (IPLMS ADR-0048). **Không phải UI sản phẩm** và không đưa ra mạng: chỉ chạy sau process `app.console_main` trên `127.0.0.1:8090`.
Thiết kế, token màu và luật giao diện: [DESIGN.md](DESIGN.md). Phía server và luồng dữ liệu: [DESIGN của ai](../DESIGN.md).

**Stack:** React 19 · TypeScript · Vite · React Router · TanStack Query · lucide-react · Vitest + Testing Library. Không có thư viện UI ngoài; component tự viết trong `src/components/common/Ui`.

## Chạy

```bash
# trong ai/
pnpm --dir ui install
pnpm --dir ui build                      # ra ui/dist; console_main phục vụ tại /console/
python -m app.console_main               # hoặc container: xem "Chạy" ở ../README.md (--profile console)
```

Mở <http://127.0.0.1:8090/console/>. Container `console` mount `ui/dist` ở chế độ chỉ đọc, nên sửa giao diện xong phải `build` lại rồi tải lại trang.

Phát triển có hot reload: để `console_main` chạy (native hoặc container), rồi `pnpm --dir ui dev` → <http://127.0.0.1:5190/>. Vite proxy `/console/api` và `/api` sang `127.0.0.1:8090`; router tự nhận basename `/console` khi URL bắt đầu bằng `/console`.

Đăng nhập: Google OIDC rồi TOTP; admin khẩn cấp đăng nhập bằng mật khẩu + TOTP. Cách tạo tài khoản test và bảng vai trò: [README của ai](../README.md#tài-khoản-test-ai-console).

## Kiểm chứng

```bash
pnpm --dir ui typecheck
pnpm --dir ui test        # vitest + Testing Library, fetch giả theo đường dẫn
pnpm --dir ui build       # tsc --noEmit && vite build
```

Có test chặn chữ tiếng Việt viết cứng ngoài từ điển (`src/i18n/noHardcodedVi.test.ts`): thêm chữ mới thì thêm vào cả `vi.ts` lẫn `en.ts`.
Phía API: `python -m unittest test.test_console_copilot_lab test.test_console_ui_serving test.test_console_http` (test có DB cần `AI_TEST_DATABASE_URL`).

## Màn hình

Đường dẫn tính từ `/console`. Mục trên thanh điều hướng hiện theo quyền và theo *không gian làm việc* (persona) chọn ở góc trên, ví dụ Toàn quyền, Kỹ sư ML, Quản trị & Kiểm toán.

| Đường dẫn | Quyền | Nội dung |
|---|---|---|
| `/` | `ai:metrics:read` | Tổng quan: tỉ lệ đúng do người chấm, số lượt, độ trễ, token, chi phí theo ngày. Không có quyền này thì chuyển tới màn đầu tiên được phép |
| `/copilot` | `ai:chatlog:read` | Chat Studio: hỏi thử Copilot có stream, hiện nguồn, tốc độ `t/s`, độ trễ; chỉnh top-k, ngưỡng, nhiệt độ |
| `/copilot/logs` | `ai:chatlog:read` (chấm: `ai:label:approve`) | Nhật ký lượt chat đã che PII: tìm kiếm, lọc trạng thái/phản hồi/khoảng thời gian, chấm Đúng/Sai/Không an toàn |
| `/knowledge` | `ai:prompt:edit` | Quản lý tri thức: danh sách tài liệu, trạng thái kiểm định, xem trước các chunk đã nạp; PDF scan OCR tối đa 20 trang mỗi lần nạp |
| `/tools` | `ai:metrics:read` hoặc `ai:prompt:edit` | Kiểm cấu hình (chỉ báo đã/chưa, không lộ giá trị), nạp bản nháp tri thức, mô phỏng Forecast — thay `/dashboard` cũ (IPLMS ADR-0050) |
| `/vision` | `ai:metrics:read` | Máy đọc đúng bao nhiêu % trên tập bốc ngẫu nhiên (khoảng tin cậy 95%), đường cong ngưỡng, đề xuất/duyệt accept policy |
| `/vision/label` | `ai:task:label` | Gán nhãn từng ảnh cắt, phím 1/2/3 |
| `/vision/review` | `ai:label:approve` | Duyệt hoặc trả lại nhãn của người khác (bốn mắt) |
| `/vision/datasets` | `ai:dataset:snapshot` hoặc `ai:model:evaluate` | Snapshot train/golden, khoá golden (AI Lead, step-up) |
| `/vision/models` | `ai:metrics:read` | Lượt đo trên golden đã khoá, đăng ký/đề xuất/promote model |
| `/members` | `ai:member:manage` | Mời, cấp/thu hồi vai trò (bắt buộc lý do, không tự cấp) |
| `/audit` | `ai:audit:read` | 200 sự kiện audit gần nhất |
| `/settings` | `ai:metrics:read`, `ai:member:manage` hoặc `ai:audit:read` | Preset phần cứng (GPU/CPU), engine LLM local, ngưỡng AI (đổi cần `ai:policy:threshold`), nạp/giải phóng model, phiên đăng nhập đang mở |

Danh sách quyền từng vai trò: [access_policy.py](../app/core/console/engines/access_policy.py). Thêm màn mới thì sửa cả `src/routes/AuthenticatedRoutes.tsx` (guard quyền) và `src/components/layout/navigation.ts` (mục điều hướng).

## Cấu trúc `src/`

| Thư mục | Vai trò |
|---|---|
| `pages/<Tên>/` | Một thư mục mỗi màn: `<Tên>Page.tsx`, `*.module.css`, `components/` riêng, test cạnh file |
| `routes/` | `AnonymousRoutes` (đăng nhập) và `AuthenticatedRoutes` (guard quyền từng màn) |
| `components/layout/` | Khung `AppShell`, thanh điều hướng, đổi persona/ngôn ngữ |
| `components/common/` | `Ui/` (nút, bảng, badge, trạng thái tải…), `Guard/`, `Boundary/`, `Fallback/`, `Shared/` |
| `services/apiEndpoints/` | Hàm gọi API theo nhóm (`tool.endpoint.ts`, `copilot.endpoint.ts`…) qua `services/apiClient.ts` |
| `api/` | Client và kiểu cũ cho phần console/auth (`client.ts`, `console.ts`) |
| `hooks/queries`, `hooks/mutations` | Hook TanStack Query; khoá cache ở `constants/queryKeys.ts` |
| `i18n/` | Từ điển `vi.ts` (gốc, định kiểu) và `en.ts` |
| `stores/` | Trạng thái nhỏ phía client: ngôn ngữ, theme, persona |
| `types/` | Kiểu dữ liệu theo nhóm API |
| `test/` | `setup.ts` và tiện ích render cho Vitest |
