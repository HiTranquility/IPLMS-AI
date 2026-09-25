# core/copilot — Trợ lý hỏi đáp quy chế (RAG) + phân xử tranh chấp

> Trạng thái (2026-09-25): hỏi đáp RAG **code thật**, cần `AI_LLM_API_KEY` (thiếu → `FAILED_PRECONDITION` "chưa được cấu hình khoá"). Phân xử tranh chấp **tắt có chủ đích** (`UNIMPLEMENTED`, bug-003); khung LangGraph có sẵn nhưng chưa nối.

## Luồng hỏi đáp (StreamAnswer / AskQuestion)

```text
backend AiCopilotController (/v1/ai/copilot/stream — SSE; preview chỉ cho người quản lý scope)
  └─ grpc CopilotService → app/api/grpc/handlers/copilot_handler.py
       └─ services/copilot_service.py              ask_question / stream_answer (preview → bản nháp)
            └─ engines/rag_pipeline.py
                 ├─ infra/embedding/embedding_client.embed_query     câu hỏi → vector 1536 (text-embedding-3-small)
                 ├─ infra/database/pgvector_client.search_similar_chunks
                 │     Hybrid: HNSW cosine (≥0.35) + full-text 'simple' → RRF k=60 → top 5
                 │     phạm vi: bãi + tài liệu chung; không có bãi → chỉ chung
                 │     góc nhìn: khách = bản PUBLISHED; preview = bản mới nhất của scope
                 ├─ không có đoạn nào → trả câu "chưa tìm thấy…", KHÔNG gọi LLM
                 └─ infra/llm/llm_factory.stream_response / generate_response
                       Responses API, SYSTEM_PROMPT: chỉ trả lời từ ngữ cảnh, trích [Nguồn], store=False
            confidence = 0.7×sim(top1) + 0.3×mean(sim)   (điểm truy xuất, không phải "độ chắc" của LLM)
```

## Phân xử tranh chấp

`copilot_service.arbitrate_dispute` → `FeatureNotImplementedError` (bản cũ luôn trả APPROVE_REFUND + bằng chứng bịa). Khung `engines/dispute_workflow/` (LangGraph: load_evidence → analyze → retrieve_policy → validate → draft → human_review → finalize, PROB-040) **chưa được gọi từ đâu**.

## File

| File | Việc |
|---|---|
| `services/copilot_service.py` | Điểm vào nghiệp vụ; chặn arbitrate |
| `engines/rag_pipeline.py` | Truy xuất → (không có ngữ cảnh thì dừng) → sinh câu trả lời; prompt + confidence |
| `engines/dispute_workflow/{graph,nodes,state,dependencies}.py` | Khung LangGraph phân xử (chưa nối) |
| `dtos/copilot_dto.py` | `AskQuestionRequest` (có `preview`), `CopilotAnswer`, `AnswerChunk` |

Tài liệu Copilot đọc được quản lý ở [core/knowledge](../knowledge/README.md) (nạp) và [core/knowledge_eval](../knowledge_eval/README.md) (test + xuất bản).

## Cấu hình

`AI_LLM_API_KEY`, `AI_LLM_MODEL` (mặc định `gpt-5.6-luna`), `AI_RAG_TOP_K=5`, `AI_RAG_MIN_SIMILARITY=0.35`, `AI_EMBEDDING_*`, `AI_DATABASE_URL` (ai-db pgvector). Test: `test_rag_pipeline.py`, `test_llm_factory.py`, `test_arbitrate_dispute.py`, `test_dispute_workflow.py`. Smoke: `python app/script/smoke_copilot_stream.py`.
