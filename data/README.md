# `data/` — dữ liệu đi kèm repo

Chỉ dữ liệu nhỏ, không nhạy cảm, cần để chạy demo và đo chất lượng. Dataset ảnh lớn và checkpoint ở `model/` (gitignored); không ghi đè file ở đây khi chưa được giao.

| Đường dẫn | Nội dung | Dùng bởi |
|---|---|---|
| `knowledge/regulations_seed.json` | Quy chế demo dùng chung (`parking_lot_id: null`), sinh bởi `python -m app.script.seed_regulations` | RAG đọc khi pgvector/embedding lỗi, và khi không có chunk nào khớp **nếu** `AI_CONSOLE_DEMO_SEED_ENABLED=true` (HiTranquility/IPLMS-AI#82) |
| `knowledge/eval_set.json` | Bộ eval RAG chính (27 ca: thường, biên, phải từ chối) | `app.script.eval_ai_engineering`, `test_eval_set` |
| `knowledge/eval_set_heldout.json` | Bộ giữ lại (32 ca), không dùng khi chỉnh prompt/ngưỡng | Báo cáo điểm trước/sau cải tiến |
| `knowledge/demo-upload/` | Tài liệu mẫu để thử nạp tri thức qua Console | [README](knowledge/demo-upload/README.md) |
| `prompts/copilot_rag_system_v2.txt` | Prompt hệ thống Copilot RAG. Sửa nội dung thì tạo file `_v3` và đổi `default_version` trong `prompt_manager.py`; log ghi `prompt_version` = tên file + hash | `app/core/copilot/engines/rag_pipeline.py` qua `prompt_manager` |
| `golden/plates/` | Manifest golden set biển số | [README](golden/plates/README.md), `training/eval_plates.py` |
| `golden/vehicle-cls/` | Chỗ cho golden set phân loại xe | `training/eval_vehicle_classifier.py` |

Đổi bộ eval thì chạy lại `eval_ai_engineering` và ghi điểm mới vào hồ sơ ISSUE liên quan; số ca và đáp án mong đợi là bằng chứng khi bảo vệ.
