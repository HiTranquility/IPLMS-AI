# 🏷️ ISSUE-017: Phần `ai` của IPLMS ISSUE-126 — AI Console nội bộ (`ai/ui`) — DB riêng, RBAC 7 vai trò, đăng nhập Google + TOTP

> **Đích:** `docs/projects/issues/10-2026/ISSUE-017-phan-ai-cua-iplms-issue-126/issue.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🚧 In progress |
| **Người phụ trách** | — |
| **Phạm vi** | `ai` |
| **Bắt nguồn từ** | IPLMS ISSUE-126 |
| **Ngày tạo** | 2026-10-25 |
| **Người viết** | Claude — chuyển từ BOARD viết tay khi BOARD chuyển sang sinh từ Meta hồ sơ (IPLMS ADR-0060) |

> BOARD sinh từ Meta và bảng `📋 Việc trên BOARD` dưới đây (IPLMS ADR-0060): đổi người nhận/hạn/trạng thái một việc thì sửa dòng của nó ở đây, **[NEVER]** sửa `BOARD.md`.

## Mục tiêu

Gom các phần việc `ai` của IPLMS ISSUE-126 đang theo dõi trên BOARD tới ngày 2026-10-25, để mỗi dòng BOARD có hồ sơ trong repo này. Ai không có quyền repo gốc: mô tả việc nằm ở cột Việc/Ghi chú dưới đây; chi tiết thêm ở IPLMS ISSUE-126.

## 📋 Việc trên BOARD

| Việc | Người nhận | Hạn | Ưu tiên | Trạng thái | Ghi chú |
|---|---|---|---|---|---|
| Đo weights ứng viên chưa nạp: nạp theo `artifact_key` trong process đo riêng (module M4) | — | — | 🟢 | 🆕 Cần người nhận | M4 chưa có người |
| AI Console nội bộ: DB riêng, 7 vai trò, đăng nhập Google + TOTP, `ai/ui` | Claude Code | — | — | 🚧 P1a–P6 + EN (`98c2a88`) + cổng từ chối RAG (`e616fee`) đã code; PR #22, #23 + nhánh xếp chồng chờ CI. Việc còn lại đã tách thành dòng riêng ngày 2026-10-18 | — |
| Hoàn thiện phần AI của `khoa-develop`: lọc thẻ `<think>`, rà `guardrail_manager`/`prompt_manager`/`ai_logger`/`llama_server_manager`, viết lại 3 test không gọi mạng | Khoa | — | — | 🚧 Giữ sửa/test trong AI; HiTranquility phụ trách nối revision/caller và tích hợp tổng thể; giao gốc 2026-10-18 | — |
| Xác nhận cột "đã kiểm/sửa" mục 3b `AI_USAGE.md` cho phần mình nhận (đề Final §5.3, thiếu là −10%) | Chủ module M1–M4 | — | — | 🚧 Mới giao 2026-10-18 | — |
| Merge chuỗi PR AI Console (ai#22, #23 → backend#24 → frontend#20 → gốc + bump gitlink → nhánh xếp chồng) | — | — | — | ⛔ Bị chặn — GitHub Actions bị từ chối do billing tài khoản | — |
| Đăng nhập Google thật cho console | — | — | — | ⛔ Bị chặn — chủ đồ án tạo OAuth client trên GCP | — |
| Chạy kênh A2 end-to-end trên stack dev (M4) | — | — | — | ⛔ Bị chặn — chủ đồ án duyệt chạy migration `1803000000000` + bật `VISION_CONSOLE_EXPORT_*` trên stack dùng chung | — |
| Mã QR TOTP ở trang đăng nhập console | — | — | — | ⛔ Bị chặn — chủ đồ án duyệt cài `segno==1.6.6` | — |

## Tiêu chí chấp nhận

- [ ] Mỗi dòng ở bảng trên chuyển sang ✅ kèm bằng chứng (ở đây hoặc ở hồ sơ gốc).
- [ ] Hết dòng mở → Trạng thái hồ sơ này ✅ + **Ngày đóng**.

## Hồ sơ liên quan

- IPLMS ISSUE-126 — mô tả đầy đủ và bằng chứng nằm ở đó.
