"""Real PostgreSQL/pgvector adapter for the Copilot knowledge base."""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

from app.config import get_config
from app.core.exceptions import RagPipelineError
from app.utils.logger import logger


class PgVectorClient:
    """Blocking psycopg2 calls isolated behind ``asyncio.to_thread``."""

    def __init__(self, db_url: str | None = None):
        config = get_config()
        self.db_url = db_url or config.llm.database_url
        self.dimensions = config.embedding.dimensions
        self._schema_ready = False
        self._schema_lock = asyncio.Lock()

    def _connect_sync(self, register: bool = True):
        try:
            import psycopg2
            from pgvector.psycopg2 import register_vector

            connection = psycopg2.connect(self.db_url, connect_timeout=5)
            if register:
                register_vector(connection)
            return connection
        except Exception as exc:
            raise RagPipelineError("Không kết nối được PostgreSQL/pgvector.") from exc

    async def connect(self) -> None:
        await self.ensure_schema()

    async def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        async with self._schema_lock:
            if self._schema_ready:
                return
            await asyncio.to_thread(self._ensure_schema_sync)
            self._schema_ready = True

    def _ensure_schema_sync(self) -> None:
        if not 1 <= self.dimensions <= 65535:
            raise RagPipelineError("AI_EMBEDDING_DIMENSIONS không hợp lệ.")
        # pgvector's adapter can only be registered after the extension exists.
        connection = self._connect_sync(register=False)
        try:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    from pgvector.psycopg2 import register_vector

                    register_vector(connection)
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS knowledge_documents (
                            id UUID PRIMARY KEY,
                            parking_lot_id VARCHAR(100),
                            file_name VARCHAR(255) NOT NULL,
                            category VARCHAR(50) NOT NULL,
                            uploaded_by VARCHAR(100),
                            status VARCHAR(32) NOT NULL DEFAULT 'SUCCESS',
                            chunk_count INTEGER NOT NULL DEFAULT 0,
                            message TEXT NOT NULL DEFAULT '',
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    cursor.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS knowledge_chunks (
                            id UUID PRIMARY KEY,
                            document_id UUID CONSTRAINT fk_knowledge_chunks_document
                                REFERENCES knowledge_documents(id) ON DELETE CASCADE,
                            parking_lot_id VARCHAR(100),
                            category VARCHAR(50) NOT NULL,
                            title VARCHAR(255),
                            content TEXT NOT NULL,
                            source VARCHAR(255) NOT NULL,
                            ordinal INTEGER NOT NULL DEFAULT 0,
                            metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                            embedding vector({self.dimensions}) NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    # Upgrade the legacy seed table without deleting its rows.
                    cursor.execute(
                        """
                        ALTER TABLE knowledge_chunks
                            ADD COLUMN IF NOT EXISTS document_id UUID,
                            ADD COLUMN IF NOT EXISTS ordinal INTEGER NOT NULL DEFAULT 0
                        """
                    )
                    cursor.execute(
                        """
                        DO $$ BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM pg_constraint
                                WHERE conname = 'fk_knowledge_chunks_document'
                            ) THEN
                                ALTER TABLE knowledge_chunks
                                ADD CONSTRAINT fk_knowledge_chunks_document
                                FOREIGN KEY (document_id)
                                REFERENCES knowledge_documents(id)
                                ON DELETE CASCADE NOT VALID;
                            END IF;
                        END $$
                        """
                    )
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_scope_category
                        ON knowledge_chunks (parking_lot_id, category)
                        """
                    )
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding_hnsw
                        ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)
                        WHERE embedding IS NOT NULL
                        """
                    )
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_content_fts
                        ON knowledge_chunks USING gin (to_tsvector('simple', content))
                        """
                    )
        except RagPipelineError:
            raise
        except Exception as exc:
            raise RagPipelineError("Không khởi tạo được schema pgvector.") from exc
        finally:
            connection.close()

    async def search_similar_chunks(
        self,
        query_embedding: List[float],
        query_text: str,
        parking_lot_id: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.35,
    ) -> List[Dict[str, Any]]:
        if len(query_embedding) != self.dimensions:
            raise RagPipelineError(
                "Số chiều query embedding không khớp schema knowledge_chunks."
            )
        await self.ensure_schema()
        return await asyncio.to_thread(
            self._search_sync,
            query_embedding,
            query_text,
            parking_lot_id,
            max(1, min(top_k, 20)),
            max(-1.0, min(min_similarity, 1.0)),
        )

    def _search_sync(
        self,
        query_embedding: List[float],
        query_text: str,
        parking_lot_id: Optional[str],
        top_k: int,
        min_similarity: float,
    ) -> List[Dict[str, Any]]:
        connection = self._connect_sync()
        try:
            with connection.cursor() as cursor:
                if parking_lot_id:
                    vector_scope_sql = "(parking_lot_id = %s OR parking_lot_id IS NULL)"
                    keyword_scope_sql = "(kc.parking_lot_id = %s OR kc.parking_lot_id IS NULL)"
                    vector_scope_params: list[Any] = [parking_lot_id]
                    keyword_scope_params: list[Any] = [parking_lot_id]
                else:
                    # A request without a lot may only see global documents;
                    # otherwise it could leak one owner's private regulation.
                    vector_scope_sql = "parking_lot_id IS NULL"
                    keyword_scope_sql = "kc.parking_lot_id IS NULL"
                    vector_scope_params = []
                    keyword_scope_params = []
                candidate_k = min(80, max(20, top_k * 4))
                cursor.execute(
                    f"""
                    WITH search_query AS (
                        SELECT websearch_to_tsquery('simple', %s) AS value
                    ),
                    vector_candidates AS (
                        SELECT id, similarity,
                               ROW_NUMBER() OVER (ORDER BY similarity DESC) AS rank
                        FROM (
                            SELECT id, 1 - (embedding <=> %s::vector) AS similarity
                            FROM knowledge_chunks
                            WHERE embedding IS NOT NULL AND {vector_scope_sql}
                        ) scored
                        WHERE similarity >= %s
                        ORDER BY similarity DESC
                        LIMIT %s
                    ),
                    keyword_candidates AS (
                        SELECT kc.id,
                               ROW_NUMBER() OVER (
                                   ORDER BY ts_rank_cd(
                                       to_tsvector('simple', kc.content), sq.value
                                   ) DESC
                               ) AS rank
                        FROM knowledge_chunks kc
                        CROSS JOIN search_query sq
                        WHERE {keyword_scope_sql}
                          AND to_tsvector('simple', kc.content) @@ sq.value
                        ORDER BY ts_rank_cd(to_tsvector('simple', kc.content), sq.value) DESC
                        LIMIT %s
                    ),
                    fused AS (
                        SELECT COALESCE(v.id, kw.id) AS id,
                               COALESCE(v.similarity, 0.0) AS similarity,
                               COALESCE(1.0 / (60 + v.rank), 0.0)
                                 + COALESCE(1.0 / (60 + kw.rank), 0.0) AS hybrid_score
                        FROM vector_candidates v
                        FULL OUTER JOIN keyword_candidates kw ON kw.id = v.id
                    )
                    SELECT kc.content, kc.category, fused.similarity,
                           kc.source, kc.metadata, kc.document_id::text, kc.ordinal,
                           fused.hybrid_score
                    FROM fused
                    JOIN knowledge_chunks kc ON kc.id = fused.id
                    ORDER BY fused.hybrid_score DESC
                    LIMIT %s
                    """,
                    [
                        query_text,
                        query_embedding,
                        *vector_scope_params,
                        min_similarity,
                        candidate_k,
                        *keyword_scope_params,
                        candidate_k,
                        top_k,
                    ],
                )
                return [
                    {
                        "content": row[0],
                        "category": row[1],
                        "similarity": float(row[2]),
                        "source": row[3],
                        "metadata": row[4] or {},
                        "document_id": row[5],
                        "ordinal": row[6],
                        "hybrid_score": float(row[7]),
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as exc:
            raise RagPipelineError("Truy vấn similarity trên pgvector thất bại.") from exc
        finally:
            connection.close()

    async def replace_document(
        self,
        *,
        document_id: str,
        file_name: str,
        category: str,
        parking_lot_id: Optional[str],
        uploaded_by: Optional[str],
        chunks: List[Dict[str, Any]],
    ) -> None:
        """Replace one document and all chunks in a single DB transaction."""
        await self.ensure_schema()
        await asyncio.to_thread(
            self._replace_document_sync,
            document_id,
            file_name,
            category,
            parking_lot_id,
            uploaded_by,
            chunks,
        )

    def _replace_document_sync(
        self,
        document_id: str,
        file_name: str,
        category: str,
        parking_lot_id: Optional[str],
        uploaded_by: Optional[str],
        chunks: List[Dict[str, Any]],
    ) -> None:
        connection = self._connect_sync()
        try:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO knowledge_documents
                            (id, parking_lot_id, file_name, category, uploaded_by, status, chunk_count)
                        VALUES (%s, %s, %s, %s, %s, 'SUCCESS', %s)
                        ON CONFLICT (id) DO UPDATE SET
                            parking_lot_id = EXCLUDED.parking_lot_id,
                            file_name = EXCLUDED.file_name,
                            category = EXCLUDED.category,
                            uploaded_by = EXCLUDED.uploaded_by,
                            status = 'SUCCESS',
                            chunk_count = EXCLUDED.chunk_count,
                            updated_at = NOW()
                        """,
                        (document_id, parking_lot_id, file_name, category, uploaded_by, len(chunks)),
                    )
                    cursor.execute(
                        "DELETE FROM knowledge_chunks WHERE document_id = %s",
                        (document_id,),
                    )
                    for chunk in chunks:
                        cursor.execute(
                            """
                            INSERT INTO knowledge_chunks
                                (id, document_id, parking_lot_id, category, title,
                                 content, source, ordinal, metadata, embedding)
                            VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                document_id,
                                parking_lot_id,
                                category,
                                chunk.get("section_title") or file_name,
                                chunk["content"],
                                file_name,
                                chunk["ordinal"],
                                json.dumps(chunk.get("metadata") or {}),
                                chunk["embedding"],
                            ),
                        )
        except Exception as exc:
            connection.rollback()
            raise RagPipelineError("Không ghi được tài liệu vào pgvector; đã rollback.") from exc
        finally:
            connection.close()

    async def delete_document(self, document_id: str, parking_lot_id: Optional[str]) -> int:
        await self.ensure_schema()
        return await asyncio.to_thread(self._delete_document_sync, document_id, parking_lot_id)

    def _delete_document_sync(self, document_id: str, parking_lot_id: Optional[str]) -> int:
        connection = self._connect_sync()
        try:
            with connection:
                with connection.cursor() as cursor:
                    scope_sql = (
                        "parking_lot_id = %s" if parking_lot_id else "parking_lot_id IS NULL"
                    )
                    params: tuple[Any, ...] = (
                        (document_id, parking_lot_id) if parking_lot_id else (document_id,)
                    )
                    cursor.execute(
                        f"SELECT COUNT(*) FROM knowledge_chunks WHERE document_id = %s AND {scope_sql}",
                        params,
                    )
                    count = int(cursor.fetchone()[0])
                    cursor.execute(
                        f"DELETE FROM knowledge_chunks WHERE document_id = %s AND {scope_sql}",
                        params,
                    )
                    cursor.execute(
                        f"DELETE FROM knowledge_documents WHERE id = %s AND {scope_sql}",
                        params,
                    )
                    return count
        except Exception as exc:
            raise RagPipelineError("Không xoá được tài liệu khỏi pgvector.") from exc
        finally:
            connection.close()


pgvector_client = PgVectorClient()
