# 📐 ADR-0001: Kho tri thức không có pgvector chỉ chạy ở dev, phải bật cờ

> **Đích:** `docs/projects/adrs/10-2026/0001-fallback-khong-pgvector-chi-cho-dev.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Accepted |
| **Ngày** | 2026-10-26 |
| **Người quyết định** | HiTranquility (chọn phương án B trong chat, 2026-10-26) |
| **Phạm vi** | IPLMS-AI: `app/infra/database/pgvector_client.py`, `app/config/embedding_config.py` |

## Bối cảnh

`PgVectorClient._ensure_schema_sync` tự dò extension `vector`. Nếu Postgres không có extension này, client lặng lẽ tạo cột `knowledge_chunks.embedding` kiểu `DOUBLE PRECISION[]` và hàm SQL `iplms_cosine_sim`. Chế độ này quét toàn bảng, không có index ANN. Nó cũng chưa từng qua cổng schema (finding A-22 của [AUDIT-006](../../audits/10-2026/AUDIT-006-console-wip-2026-10-25.md), theo dõi ở [ISSUE-019](../../issues/10-2026/ISSUE-019-console-settings-va-don-audit-006/issue.md)).

Có hai rủi ro:
- Production trỏ nhầm vào Postgres thường vẫn chạy được, nhưng chậm, và không ai biết.
- Bảng đã tạo ở kiểu mảng sẽ lệch kiểu cột khi sau này cài pgvector, vì lệnh dùng `CREATE TABLE IF NOT EXISTS` nên không tạo lại bảng.

Compose (`database-vector`) và CI (`.github/workflows/ci.yml`) đều dùng image `pgvector/pgvector`. Riêng máy dev chạy Postgres thuần trên Windows thì không có extension.

## Quyết định

Giữ fallback mảng nhưng mặc định tắt. Fallback chỉ chạy khi đặt `AI_EMBEDDING_ALLOW_NO_PGVECTOR=true`. Nếu thiếu pgvector mà cờ đang tắt, client ném `RagPipelineError` với hướng dẫn rõ ràng, trước khi tạo bất kỳ bảng hay hàm nào. Khi fallback chạy, client ghi log `WARNING`. Cờ này **không bao giờ** được bật ở production. Compose production không đặt cờ, nên production dùng mặc định là tắt.

## Các phương án đã cân nhắc

- **A. Bỏ fallback, bắt buộc pgvector.** Chỉ còn một lược đồ duy nhất, nhưng máy dev không có container pgvector sẽ không chạy được kho tri thức. Không chọn, để thành viên dev bằng Postgres thuần vẫn làm việc được.
- **C. Giữ nguyên hành vi, chỉ viết ADR.** Không tốn công, nhưng không chặn được production lặng lẽ chạy chế độ chậm. Không chọn.

## Hệ quả

### Được

- Production và CI luôn có pgvector, hoặc dừng ngay với lỗi rõ ràng.
- Dev không có pgvector vẫn chạy được khi chủ động bật cờ.

### Đánh đổi

- Vẫn phải duy trì hai kiểu cột và hai biểu thức tính độ tương đồng (`pgvector_client.py`).
- Bảng tạo ở chế độ mảng không tự chuyển sang kiểu `vector` khi về sau có pgvector. Muốn chuyển thì phải xoá rồi nạp lại kho tri thức của máy dev đó.

## Bằng chứng và liên kết

- Code: `app/config/embedding_config.py` (`allow_no_pgvector`), `app/infra/database/pgvector_client.py` (`_ensure_schema_sync`), `.env.example`.
- Test: `test/test_pgvector_fallback_flag.py`.
- Hồ sơ: [ISSUE-019](../../issues/10-2026/ISSUE-019-console-settings-va-don-audit-006/issue.md), finding A-22.
