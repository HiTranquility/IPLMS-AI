# Guides AI — lộ trình đọc

Tài liệu lý thuyết và chiến lược xây dựng cho ba pipeline IPLMS. Hai guide đầu được chỉnh từ bản đã có; các guide dùng khung [guide-template](../../../docs/templates/guide/guide-template.md), giữ trong `ai/docs/guides/` theo yêu cầu.

| Thứ tự | Guide | Đọc để hiểu |
|---|---|---|
| 1 | [Ba pipeline AI](09-2026/01-three-ai-pipelines-architecture.md) | Vision, Copilot/RAG, Forecast nối backend thế nào; phần nào đã có |
| 2 | [RAG và chiến lược tối ưu](09-2026/02-rag-optimization-strategy.md) | 8 bước ingest, 9 bước query, chunking, retrieval, evaluation và roadmap |
| 3 | [Xử lý ảnh ANPR](09-2026/03-image-processing-pipeline.md) | 8 bước logic, 6 phép tiền xử lý, OCR, confidence, vòng dữ liệu/model |
| 4 | [Forecast và huấn luyện](09-2026/04-forecast-training-strategy.md) | 8 bước từ nhãn thời gian đến backtest, phục vụ và policy giá |
| 5 | [Worker, storage và vòng đời dữ liệu AI](09-2026/05-ai-workers-storage-and-training-lifecycle.md) | Tách engine/service, việc nào dùng RabbitMQ, chọn object storage và đưa ảnh đã duyệt tới model |
| 6 | [Google Colab training](09-2026/06-google-colab-training-runbook.md) | Đưa snapshot lên Colab, train/resume/evaluate, đóng gói và đưa model candidate về kho bền |
| 7 | [Seed → data lake → cloud source map](09-2026/07-seed-datalake-cloud-source-map.md) | Lần từ lệnh tới code, chạy seed/export local và xác định chính xác phần S3/cloud còn thiếu |

Đối chiếu mã nguồn đến ngày **2026-09-21**; Vision/Forecast data-path và source map seed/data-lake/cloud nằm trong guide 3–7. Các mục **đề xuất/mục tiêu** chưa phải tính năng đã chạy. Bộ tài liệu chưa chứng nhận chất lượng production; phần kiểm chứng mỗi guide chỉ rõ cách đánh giá tiếp.

[AI README](../../README.md) · [AI conventions](../standards/AI_CONVENTIONS.md)
