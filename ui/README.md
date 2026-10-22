# AI Console UI (`ai/ui`)

Giao diện nội bộ của bộ phận AI (IPLMS ADR-0048). **Không phải UI sản phẩm**, không đưa ra mạng: chỉ chạy sau process `app.console_main` trên `127.0.0.1:8090`. Thiết kế và luật giao diện: [DESIGN.md](DESIGN.md).

## Chạy

```bash
# trong ai/
pnpm --dir ui install
pnpm --dir ui build                      # ra ui/dist, console_main phục vụ tại /console/
python -m app.console_main               # hoặc: docker compose --profile console up console
```

Mở `http://localhost:8090/console/`. Phát triển giao diện có hot reload: chạy `console_main` như trên rồi `pnpm --dir ui dev` (cổng 5190, proxy `/console/api` sang 8090).

## Kiểm chứng

```bash
pnpm --dir ui typecheck
pnpm --dir ui test        # vitest + Testing Library, fetch giả theo đường dẫn
pnpm --dir ui build
```

Phía API: `python -m unittest test.test_console_copilot_lab test.test_console_ui_serving test.test_console_http` (test có DB cần `AI_TEST_DATABASE_URL`).

## Màn hình

| Đường dẫn | Quyền | Nội dung |
|---|---|---|
| `/console/` | `ai:metrics:read` | Tỉ lệ đúng do người chấm, mức dùng, độ trễ, token, chi phí, theo ngày |
| `/console/copilot` | `ai:chatlog:read` (chấm: `ai:label:approve`) | Lượt chat đã che PII, lọc trạng thái/phản hồi, chấm Đúng/Sai/Không an toàn |
| `/console/tools` | `ai:metrics:read` (hỏi thử, nạp: `ai:prompt:edit`) | Kiểm cấu hình (chỉ đã/chưa), hỏi thử Copilot (task `console_try`, không vào số sản phẩm), nạp bản nháp tri thức — thay `/dashboard` cũ (IPLMS ADR-0050) |
| `/console/members` | `ai:member:manage` | Mời, cấp/thu hồi vai trò (bắt buộc lý do, không tự cấp) |
| `/console/audit` | `ai:audit:read` | 200 sự kiện audit gần nhất |
| `/console/vision` | `ai:metrics:read` | Máy đọc đúng bao nhiêu % trên tập bốc ngẫu nhiên (khoảng tin cậy 95%), đường cong ngưỡng, đề xuất/duyệt accept policy, trạng thái nhận A2 |
| `/console/vision/label` | `ai:task:label` | Gán nhãn từng ảnh cắt, phím 1/2/3 như trang moderator |
| `/console/vision/review` | `ai:label:approve` | Duyệt/trả lại nhãn của người khác (bốn mắt) |
| `/console/vision/datasets` | `ai:dataset:snapshot` hoặc `ai:model:evaluate` | Snapshot train/golden, khoá golden (AI Lead, step-up) |
| `/console/vision/models` | `ai:metrics:read` | Lượt đo trên golden đã khoá, đăng ký/đề xuất/promote model |
