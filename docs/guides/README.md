# Guides AI — lộ trình đọc

Tài liệu lý thuyết và chiến lược xây dựng cho ba pipeline IPLMS. Hai guide đầu được chỉnh từ bản đã có; các guide dùng khung [guide-template](../../../docs/templates/guide-template.md), giữ trong `ai/docs/guides/` theo yêu cầu.

| Thứ tự | Guide | Đọc để hiểu |
|---|---|---|
| 1 | [Ba pipeline AI](./01-three-ai-pipelines-architecture.md) | Vision, Copilot/RAG, Forecast nối backend thế nào; phần nào đã có |
| 2 | [RAG và chiến lược tối ưu](./02-rag-optimization-strategy.md) | 8 bước ingest, 9 bước query, chunking, retrieval, evaluation và roadmap |
| 3 | [Xử lý ảnh ANPR](./03-image-processing-pipeline.md) | 8 bước logic, 6 phép tiền xử lý, OCR, confidence, vòng dữ liệu/model |
| 4 | [Forecast và huấn luyện](./04-forecast-training-strategy.md) | 8 bước từ nhãn thời gian đến backtest, phục vụ và policy giá |

Đối chiếu mã nguồn ngày **2026-09-19**. Các mục **đề xuất/mục tiêu** chưa phải tính năng đã chạy. Bộ tài liệu chưa chứng nhận chất lượng production; phần kiểm chứng mỗi guide chỉ rõ cách đánh giá tiếp.

[AI README](../../README.md) · [AI conventions](../AI_CONVENTIONS.md)
