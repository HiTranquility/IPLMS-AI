# `test/` — test Python (`unittest`)

Một file mỗi module, tên `test_<module>.py`. Không dùng pytest; image `iplms-ai` không cài pytest.

## Chạy

```bash
# trong ai/, một lần sau khi clone hoặc đổi proto
python app/script/compile_proto.py

python -m unittest discover -s test -t .          # toàn bộ
python -m unittest test.test_rag_pipeline         # một module (ưu tiên khi sửa ít)
```

- **Thiếu bước `compile_proto`** thì các test gRPC (`test_console_vision_import`, `test_copilot_usage.GrpcHandlerTest`…) báo `ERROR` lúc import. CI chạy bước này trước ([ci.yml](../.github/workflows/ci.yml)).
- Máy không có đủ thư viện (cv2, fastapi, grpc…) thì chạy trong image, mount mã ở chế độ ghi được (logger tạo `var/log`):
  ```bash
  docker run --rm --network none -v "$PWD:/src" -w /src --entrypoint python iplms-ai:latest -m unittest discover -s test -t .
  ```
- Test cần DB thật đọc `AI_TEST_DATABASE_URL`; không đặt thì tự `skip`, không báo lỗi.

## Nhóm test

| Nhóm | File tiêu biểu |
|---|---|
| Vision/ANPR | `test_anpr_pipeline`, `test_plate_text`, `test_two_line_plate_parser`, `test_vehicle_classifier`, `test_vision_integration_regression` |
| Copilot/RAG, guardrail | `test_rag_pipeline`, `test_output_guard`, `test_injection_scan`, `test_keyword_search`, `test_llm_factory`, `test_copilot_streaming_api` |
| Tri thức | `test_document_parser`, `test_chunker`, `test_ingestion_service`, `test_knowledge_eval`, `test_eval_set` |
| AI Console | `test_console_auth`, `test_console_access`, `test_console_http`, `test_console_tools`, `test_console_vision_lab`, `test_console_db_hardening` |
| Dataset, model | `test_dataset_curation`, `test_dataset_evaluation`, `test_model_artifact_registry`, `test_model_policy`, `test_training_readiness` |
| Forecast, datalake | `test_forecast_service`, `test_parquet_lake_reader`, `test_lakehouse_forecast_e2e` |
| Hợp đồng, hạ tầng | `test_enums_match_proto`, `test_config`, `test_docker_context`, `test_pgvector_fallback_flag` |

Bộ eval AI theo §4.2 của đề (ca mong đợi, ca phải từ chối) không nằm ở đây mà ở [data/knowledge](../data/README.md), chạy bằng `python -m app.script.eval_ai_engineering`; `test_eval_set` chỉ kiểm định dạng của bộ đó.
