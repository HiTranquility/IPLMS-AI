"""RAG Pipeline Engine (LangChain + pgvector)."""
from typing import Dict, Any, AsyncGenerator
from app.infra.database.pgvector_client import pgvector_client
from app.infra.llm.llm_factory import llm_factory
from app.utils.logger import logger

class RagPipelineEngine:
    async def query(self, query_text: str, parking_lot_id: str = None) -> Dict[str, Any]:
        logger.info(f"Executing RAG pipeline for query: {query_text}")
        dummy_embedding = [0.0] * 1536
        chunks = await pgvector_client.search_similar_chunks(dummy_embedding, parking_lot_id, top_k=2)
        context_str = "\n".join([f"- {c['content']} (Nguồn: {c['source']})" for c in chunks])
        sources = [c["source"] for c in chunks]

        answer = await llm_factory.generate_response("Bạn là Trợ lý Bãi đỗ xe thông minh IPLMS.", query_text, context_str)

        return {
            "answer": answer,
            "sources": sources,
            "confidence": 0.95
        }

    async def stream_query(self, query_text: str, parking_lot_id: str = None) -> AsyncGenerator[Dict[str, Any], None]:
        logger.info(f"Executing RAG streaming pipeline for query: {query_text}")
        dummy_embedding = [0.0] * 1536
        chunks = await pgvector_client.search_similar_chunks(dummy_embedding, parking_lot_id, top_k=2)
        sources = [c["source"] for c in chunks]
        context_str = "\n".join([f"- {c['content']}" for c in chunks])

        async for token in llm_factory.stream_response("System Prompt", query_text, context_str):
            yield {
                "token": token,
                "is_finished": False,
                "sources": sources
            }
        
        yield {
            "token": "",
            "is_finished": True,
            "sources": sources
        }

rag_pipeline = RagPipelineEngine()
