# DESIGN — AI Console UI

Trạng thái: thiết kế hiện hành của P1c (IPLMS ISSUE-126), 2026-10-16. Quyết định gốc: IPLMS [ADR-0048](../../docs/projects/adrs/10-2026/0048-ai-console-noi-bo-trong-khoi-ai.md) (console nội bộ trong khối AI), [ADR-0049](../../docs/projects/adrs/10-2026/0049-telemetry-ai-luu-o-ai-db-dashboard-o-platform.md) (telemetry ở `ai-db`). Điểm vào: [README](README.md).

## Vị trí và ranh giới

- App React độc lập trong repo AI, **không** thuộc monorepo `frontend/` và không import `@iplms/shared`: console chỉ nói chuyện với `app.console_main` cùng nguồn (`/console/api`), không gọi backend NestJS.
- Phiên là cookie httpOnly `SameSite=Strict` do server đặt; UI không đọc/lưu token. Mọi request ghi gửi `X-Console-Request: 1` (chống CSRF, kiểm ở `app/api/rest/console_access.py`).
- Ẩn nút/menu theo `permissions` của `/me` chỉ là tiện dụng; backend kiểm quyền ở mọi route.
- Build ra `ui/dist`; `console_main` phục vụ SPA với CSP `default-src 'self'` — không CDN, không font ngoài, không script inline.

## Cấu trúc

```text
src/
  api/          client.ts (fetch + envelope + ApiError), console.ts (endpoint), types.ts, queryKeys.ts
  hooks/        useConsole.ts, useVision.ts — mọi useQuery/useMutation, queryKey lấy từ QUERY_KEYS
  components/
    common/Ui/{button,data-display,feedback,form,media}/   component có props
    common/Shared/                                         màn hình tĩnh (Forbidden, NotFound)
    layout/                                                AppShell (rail trái), PageHeader, navigation, LanguageSwitch
  i18n/         vi.ts (từ điển gốc, kiểu `Messages`), en.ts, I18nProvider (useI18n)
  pages/{Auth,Overview,Copilot,Tools,Members,Audit,Vision}/
  test/         setup + helper giả fetch
  utils/        format.ts (số/ngày theo ngôn ngữ), lang.ts, theme.ts
```

Đặt tên khớp `frontend` (`packages/platform/src/pages/Common/Auth`): thư mục page `PascalCase`; component/page `PascalCase.tsx` + `PascalCase.module.css` đặt cạnh; CSS dùng chung cả thư mục viết thường (`auth.module.css`, `vision.module.css`, `Ui/data-display/table.module.css`); helper `camelCase.ts`.

Theo cùng luật `Shared/` vs `Ui/<nhóm>/` của `frontend/` (IPLMS PAT-006). Primitive chép từ `@iplms/shared` ghi nguồn ở đầu file (`frontend@b4eaa5c`); `Button` bỏ bóng màu và hiệu ứng nhấc nút cho đúng luật "không glow".

## Thị giác — Graphite & Amber

Cùng **tên** token với 3 app frontend (`--color-bg`, `--color-surface*`, `--color-primary*`, `--color-accent*`, `--color-accent-ink`…), **giá trị** riêng trong `src/index.css`, cố ý khác Emerald (client), Royal Blue (operator), Signal Red (platform) để không ai nhầm console với UI sản phẩm.

| Token | Sáng | Tối | Dùng cho |
|---|---|---|---|
| `--color-primary` | `#24272b` graphite | `#ecebe7` | CTA chính, segment đang chọn |
| `--color-accent` | `#d97706` amber | `#f59e0b` | Viền mục đang chọn, nút "Lưu kết quả", nhãn phạm vi |
| `--color-accent-ink` | `#1c1204` | `#1c1204` | Chữ trên nền accent |
| `--color-accent-dark` | `#92400e` | `#fbbf24` | Chữ accent trên nền thường |

Font hệ thống (`system-ui`, `ui-monospace`) — không tải font. Theme sáng/tối theo hệ điều hành, đổi tay ở rail và nhớ trong `localStorage`.

## Ngôn ngữ — VI/EN

- Từ điển tự viết, **không** dùng `i18next` như `frontend/` (IPLMS ISSUE-126 6.13, người dùng chọn 2026-10-17): 0 package mới, đúng ranh giới "không import `@iplms/shared`". `src/i18n/vi.ts` là khuôn `Messages`; `en.ts` khai `en: Messages` nên thiếu/thừa khoá là `tsc` báo lỗi — cổng L5 kiểm bằng typecheck. Câu có số/tên là hàm nhận chuỗi đã định dạng.
- Component đọc `const { t } = useI18n()`; code ngoài React (`api/client.ts`) dùng `messages()`. Nhãn enum (trạng thái, kết luận, giai đoạn model) nằm trong từ điển; `labels.ts` chỉ còn tông Badge.
- Mặc định tiếng Việt; đổi ở rail và ở trang đăng nhập/TOTP (`LanguageSwitch`, nhãn nhóm hai thứ tiếng), nhớ ở `localStorage` `ai-console-lang`, đặt `<html lang>`. Số/ngày theo `vi-VN`/`en-US`, múi giờ vẫn `Asia/Ho_Chi_Minh`; tiền luôn USD.
- Server viết thông điệp lỗi bằng tiếng Việt. `ErrorBlock` ở EN hiện câu dịch theo `code` (`errors.serverCodes`), giữ nguyên văn server (`lang="vi"`) và mã bên dưới; mã không có trong bảng thì hiện nguyên văn. `ApiError.fromServer` phân biệt câu của server với câu client tự đặt theo ngôn ngữ đang dùng.
- Chữ server gửi kèm dữ liệu: nhãn mục kiểm ở Công cụ thử dịch theo `key` (`tools.checks`); lý do ngưỡng đề xuất dựng lại ở client từ `total/min_samples/target/suggested_threshold` theo đúng luật `audit_accuracy.py` (bỏ `suggestion_reason`). Dữ liệu (câu hỏi, câu trả lời, lý do người nhập, lỗi nhận A2) giữ nguyên văn.

## Luật Hallmark áp dụng (frontend/DESIGN.md §4)

1. Icon chỉ `lucide-react`, không emoji.
2. Không bịa số: không có dữ liệu thì `—` hoặc empty state nói rõ lý do (vd. chưa cấu hình giá → chi phí `—`; chưa chấm lượt nào → tỉ lệ đúng `—`).
3. Không gradient/glow; phân cấp bằng hairline, surface, chữ đậm.
4. Không `transition: all`; hover chỉ trong `@media (hover: hover)`; focus ring hiện ngay.
5. Danh sách dùng row + rail bất đối xứng (Copilot Lab: danh sách 2fr / chi tiết 3fr), không lưới card.
6. Số dùng `tabular-nums`; control cao tối thiểu 44px trên màn cảm ứng (`pointer: coarse`); với chuột, nút `sm` và segmented thấp hơn (32–36px) cho mật độ bảng.
7. Mọi màn hình dữ liệu có loading, empty, error (kèm mã lỗi và "Thử lại").
8. Màu/font chỉ qua token; mỗi theme có `--color-accent-ink`.

## Ngoại lệ và việc chưa làm

| Mục | Hiện trạng | Khi nào xử lý |
|---|---|---|
| Mã QR TOTP | Hiện khoá để nhập tay, không thêm lib QR | Nếu cần, chọn lib tự chứa không CDN và hỏi trước khi cài |

**Step-up tại chỗ:** `Ui/form/ReasonAction` bắt mọi thao tác nhạy cảm ghi lý do; server trả `STEP_UP_REQUIRED` thì hiện ô mã TOTP ngay trong form rồi làm tiếp (khoá golden, promote model, duyệt ngưỡng). Nút bị khoá kèm lý do khi người xem chính là người đề xuất (bốn mắt) — backend vẫn chặn lại.
