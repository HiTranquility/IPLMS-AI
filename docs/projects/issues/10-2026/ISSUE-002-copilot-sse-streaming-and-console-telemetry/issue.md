# 🏷️ ISSUE-002: Copilot SSE Streaming & Console Telemetry Integration

> **Đích:** `docs/projects/issues/10-2026/ISSUE-002-copilot-sse-streaming-and-console-telemetry/issue.md`

| | |
|---|---|
| **Trạng thái** | 🚧 In progress |
| **Ngày tạo** | 2026-10-18 |
| **Người phụ trách** | Khoa (khoalololo) |
| **Phạm vi** | IPLMS-AI: Copilot SSE streaming, launcher Windows, telemetry analytics |

## Mục tiêu

Hợp nhất các tính năng từ nhánh `khoa-develop` vào hệ thống kiến trúc mới của `develop`:
1. Server-Sent Events (SSE) streaming cho Copilot RAG pipeline (`/api/copilot/stream`).
2. Tích hợp số liệu viễn trắc AI Telemetry & Cost Summary (`/api/copilot/metrics`).
3. Đồng bộ giao diện Web UI AI Console và bộ launcher Windows.

## Tiêu chí chấp nhận (Definition of Done / Acceptance Criteria)

- [x] Merge `origin/develop` vào `khoa-develop`, xử lý sạch 6 file xung đột.
- [x] Stream SSE hoạt động ổn định với đầy đủ rào chắn Guardrail (Prompt Injection, Out of Scope).
- [x] Vượt qua toàn bộ unit tests, đặc biệt là `test/test_copilot_streaming_api.py`.
- [x] Tuân thủ quy chuẩn ADR-0048, ADR-0049, ADR-0050.

## Hồ sơ liên quan

- PR #39
- ADR-0048, ADR-0049, ADR-0050, ADR-0053
